import logging
import statistics
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Deque, Any

from vrchat_osc_scripts.clients.receiver import VRChatOSCReceiver
from vrchat_osc_scripts.clients.sender import VRChatOSCSender
from vrchat_osc_scripts.handlers.base import BaseHandler

logger = logging.getLogger(__name__)

@dataclass(slots=True, kw_only=True)
class Mood:
    name: str
    hr_start: int | None
    hr_end: int | None
    stabilisation_window_map: dict[str, timedelta]
    order: int

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, Mood):
            return self.order > other.order
        raise ValueError("")

    def __hash__(self) -> int:
        return hash(self.name)

MOODS = [
    Mood(
        name="deep sleeping",
        hr_start=None,
        hr_end=50,
        stabilisation_window_map={
            "sleeping": timedelta(minutes=1)
        },
        order=0,
    ),
    Mood(
        name="sleeping",
        hr_start=50,
        hr_end=60,
        stabilisation_window_map={
            "deep sleeping": timedelta(minutes=1),
            "comfy": timedelta(minutes=2),
        },
        order=1,
    ),
    Mood(
        name="comfy",
        hr_start=60,
        hr_end=80,
        stabilisation_window_map={
            "sleeping": timedelta(minutes=2),
            "normal": timedelta(minutes=2),
        },
        order=2,
    ),
    Mood(
        name="normal",
        hr_start=80,
        hr_end=110,
        stabilisation_window_map={
            "comfy": timedelta(minutes=2),
            "active": timedelta(minutes=1),
        },
        order=3,
    ),
    Mood(
        name="active",
        hr_start=110,
        hr_end=135,
        stabilisation_window_map={
            "normal": timedelta(minutes=2),
            "intense": timedelta(seconds=10),
        },
        order=4,
    ),
    Mood(
        name="intense",
        hr_start=135,
        hr_end=150,
        stabilisation_window_map={
            "active": timedelta(seconds=10),
            "super intense": timedelta(seconds=10),
        },
        order=5,
    ),
    Mood(
        name="super intense",
        hr_start=150,
        hr_end=None,
        stabilisation_window_map={
            "intense": timedelta(seconds=10),
        },
        order=6,
    ),
]
MOOD_MAP = {mood.name: mood for mood in MOODS}
TRANSITION_MOODS = [
    "excited",
    "calming"
]


class HeartRateChatBoxUpdateHandler(BaseHandler):
    """
    Handler that derives a textual “mood” from heart‑rate samples and posts it
    into VRChat’s chatbox.
    """

    # ---------- Tuning constants ---------------------------------------------
    HISTORY_SIZE: int = 180                 # Max samples in history (~3 min at 1 Hz)
    BASELINE_WINDOW_SEC: int = 30           # Rolling baseline window for median
    STATE_STABILISATION_SEC: int = 10       # …N seconds before we accept new mood

    SUDDEN_JUMP_BPM: int = 18
    SUDDEN_JUMP_WINDOW_SEC: int = 30
    SUDDEN_DROP_BPM: int = 18
    SUDDEN_DROP_WINDOW_SEC: int = 30

    SIGNIFICANT_DELTA_BPM: int = 12         # Notify on big delta inside same mood

    # -------------------------------------------------------------------------

    def __init__(
        self,
        sender: VRChatOSCSender,
        receiver: VRChatOSCReceiver,
    ):
        super().__init__(sender, receiver)
        self._hr_history: Deque[tuple[datetime, float]] = deque(maxlen=self.HISTORY_SIZE)

        self._current_mood: str | None = None       # debounced, last published
        self._pending_mood: tuple[str, datetime] | None = None  # (mood, first_seen)

        self._last_notified_bpm: float | None = None

    # -------------------------------------------------------------------------

    def on_parameter_changed(self, parameter: str, hr: int) -> None:
        if parameter != "Normalised":
            return

        try:
            hr = float(hr) * 250  # Denormalize before validation
        except (TypeError, ValueError):
            logger.warning(f"Invalid heart‑rate value: {hr}")
            return

        now = datetime.now(timezone.utc)
        self._hr_history.append((now, hr))

        baseline = self._compute_baseline(now, exclude_latest=True)

        last_sample = self._hr_history[-2] if len(self._hr_history) >= 2 else None
        last_hr, last_ts = (last_sample[1], last_sample[0]) if last_sample else (None, None)
        candidate_mood = self._derive_mood(hr, baseline)

        # ---------------- Debounce mood changes ----------------
        self._update_debounced_state(candidate_mood, now)

        # # --------------- Big delta announcements ---------------
        # if (
        #     self._current_mood is not None
        #     and last_hr is not None
        #     and abs(hr - last_hr) >= self.SIGNIFICANT_DELTA_BPM
        #     and (self._last_notified_bpm is None or abs(hr - self._last_notified_bpm) >= self.SIGNIFICANT_DELTA_BPM)
        # ):
        #     if hr > last_hr:
        #         vector = "↑↑"
        #     else:
        #         vector = "↓↓"
        #     mood_message = f"♡ {vector} {hr} - {self._current_mood}"
        #     self.send_new_mood_state(mood_message)
        #     self._last_notified_bpm = hr

    # -------------------------------------------------------------------------

    def _update_debounced_state(self, candidate: str, now: datetime) -> None:
        """Accept *candidate* as the new public mood only if it remains unchanged
        for ``STATE_STABILISATION_SEC`` seconds."""

        if self._current_mood is None:
            # First sample – publish immediately
            self._current_mood = candidate
            self.send_new_mood_state(candidate)
            return

        if candidate == self._current_mood:
            # Still in the same mood – clear any pending transition
            self._pending_mood = None

        if any(candidate.startswith(transition_mood) for transition_mood in TRANSITION_MOODS):
            self.send_new_mood_state(candidate)
            return

        # Mood differs from the one currently published
        if self._pending_mood is None or self._pending_mood[0] != candidate:
            # New candidate – start timing
            self._pending_mood = (candidate, now)
            # logger.debug(f"Mood candidate {candidate} detected; waiting for stability")
            return

        # Candidate unchanged – check dwell time
        first_seen = self._pending_mood[1]
        if (now - first_seen).total_seconds() >= self.STATE_STABILISATION_SEC:
            old_mood = MOOD_MAP[self._current_mood]
            new_mood = MOOD_MAP[self._pending_mood]
            if new_mood > old_mood:
                vector = "↑"
            else:
                vector = "↓"
            self._current_mood = candidate
            self._pending_mood = None
            mood_message = f"♡ {vector} {self._hr_history[-1][1]} - {self._current_mood}"
            self.send_new_mood_state(mood_message)
            logger.debug(f"Mood changed to {candidate} after stabilisation")

    # -------------------------------------------------------------------------

    def _compute_baseline(self, now: datetime, *, exclude_latest: bool) -> float | None:
        cutoff = now - timedelta(seconds=self.BASELINE_WINDOW_SEC)
        samples: list[float] = [
            bpm
            for ts, bpm in list(self._hr_history)[: len(self._hr_history) - (1 if exclude_latest else 0)]
            if ts >= cutoff
        ]
        return statistics.median(samples) if samples else None

    # -------------------------------------------------------------------------

    def _derive_mood(self, hr: float, baseline: float | None) -> str:
        # Deviation from rolling baseline
        if baseline is not None:
            delta = hr - baseline
            if delta >= self.SUDDEN_JUMP_BPM:
                return f"♡ excited (+{delta} in {self.BASELINE_WINDOW_SEC}s)"
            if delta <= -self.SUDDEN_DROP_BPM:
                return f"♡ calming (-{delta} in {self.BASELINE_WINDOW_SEC}s)"

        # Bucket by absolute zones
        return self._bucket_mood(hr)

    # -------------------------------------------------------------------------

    def _bucket_mood(self, hr: float) -> str:
        for mood in MOODS:
            if mood.hr_start is None and hr < mood.hr_end:
                return mood.name
            if mood.hr_end is None and hr >= mood.hr_start:
                return mood.name
            if mood.hr_start is not None and mood.hr_end is not None and mood.hr_start <= hr < mood.hr_end:
                return mood.name
        raise ValueError(hr)

    # -------------------------------------------------------------------------

    def send_new_mood_state(self, message: str) -> None:
        logger.info(f"Announcing mood: {message}")
        self._sender.send_to_chat(message)
