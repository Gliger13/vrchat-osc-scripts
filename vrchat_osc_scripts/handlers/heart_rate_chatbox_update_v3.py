import logging
import statistics
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Deque, List, Tuple

from vrchat_osc_scripts.clients.receiver import VRChatOSCReceiver
from vrchat_osc_scripts.clients.sender import VRChatOSCSender
from vrchat_osc_scripts.handlers.base import BaseHandler

logger = logging.getLogger(__name__)


class HeartRateChatBoxUpdateHandler(BaseHandler):
    """
    Handler that derives a textual “mood” from heart‑rate samples and posts it
    into VRChat’s chatbox.

    Compared to the original version this class now *debounces* mood changes:
    a new mood must stay stable for ``STATE_STABILISATION_SEC`` seconds before
    it is announced.  This prevents rapid state flapping such as
    “normal → active → normal” in back‑to‑back seconds.
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
        self._hr_history: Deque[Tuple[datetime, float]] = deque(maxlen=self.HISTORY_SIZE)

        self._current_mood: str | None = None       # debounced, last published
        self._pending_mood: Tuple[str, datetime] | None = None  # (mood, first_seen)

        self._last_notified_bpm: float | None = None

    # -------------------------------------------------------------------------

    def on_parameter_changed(self, parameter, hr) -> None:
        if parameter != "Normalised":
            return

        try:
            hr = float(hr) * 250          # Denormalise before validation
        except (TypeError, ValueError):
            logger.warning("Invalid heart‑rate value: %s", hr)
            return

        now = datetime.now(timezone.utc)
        self._hr_history.append((now, hr))

        baseline = self._compute_baseline(now, exclude_latest=True)
        last_sample = self._hr_history[-2] if len(self._hr_history) >= 2 else None
        last_hr, last_ts = (last_sample[1], last_sample[0]) if last_sample else (None, None)

        candidate_mood = self._derive_mood(hr, baseline, last_hr, last_ts, now)

        # ---------------- Debounce mood changes ----------------
        self._update_debounced_state(candidate_mood, now)

        # --------------- Big delta announcements ---------------
        if (
            self._current_mood is not None
            and last_hr is not None
            and abs(hr - last_hr) >= self.SIGNIFICANT_DELTA_BPM
            and (self._last_notified_bpm is None or abs(hr - self._last_notified_bpm) >= self.SIGNIFICANT_DELTA_BPM)
        ):
            self.send_new_mood_state(f"{self._current_mood} ({int(last_hr)} → {int(hr)})")
            self._last_notified_bpm = hr

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
            return

        # Mood differs from the one currently published
        if self._pending_mood is None or self._pending_mood[0] != candidate:
            # New candidate – start timing
            self._pending_mood = (candidate, now)
            logger.debug("Mood candidate %s detected; waiting for stability", candidate)
            return

        # Candidate unchanged – check dwell time
        first_seen = self._pending_mood[1]
        if (now - first_seen).total_seconds() >= self.STATE_STABILISATION_SEC:
            self._current_mood = candidate
            self._pending_mood = None
            self.send_new_mood_state(candidate)
            logger.debug("Mood changed to %s after stabilisation", candidate)

    # -------------------------------------------------------------------------

    def _compute_baseline(self, now: datetime, *, exclude_latest: bool) -> float | None:
        cutoff = now - timedelta(seconds=self.BASELINE_WINDOW_SEC)
        samples: List[float] = [
            bpm
            for ts, bpm in list(self._hr_history)[: len(self._hr_history) - (1 if exclude_latest else 0)]
            if ts >= cutoff
        ]
        return statistics.median(samples) if samples else None

    # -------------------------------------------------------------------------

    def _derive_mood(
        self,
        hr: float,
        baseline: float | None,
        last_hr: float | None,
        last_ts: datetime | None,
        now: datetime,
    ) -> str:
        # Short‑term sudden jumps / drops
        if last_hr is not None and last_ts is not None:
            dt = (now - last_ts).total_seconds()
            if hr - last_hr >= self.SUDDEN_JUMP_BPM and dt <= self.SUDDEN_JUMP_WINDOW_SEC:
                return "♡ excited"
            if last_hr - hr >= self.SUDDEN_DROP_BPM and dt <= self.SUDDEN_DROP_WINDOW_SEC:
                return "♡ calming"

        # Deviation from rolling baseline
        if baseline is not None:
            delta = hr - baseline
            if delta >= self.SUDDEN_JUMP_BPM:
                return "♡ excited"
            if delta <= -self.SUDDEN_DROP_BPM:
                return "♡ calming"

        # Bucket by absolute zones
        return self._bucket_mood(hr)

    # -------------------------------------------------------------------------

    def _bucket_mood(self, hr: float) -> str:
        zones = {
            "♡ deep sleeping": (None, 50),
            "♡ sleeping": (50, 60),
            "♡ comfy": (60, 79),
            "♡ normal": (79, 110),
            "♡ active": (110, 135),
            "♡ intense": (135, None),
        }
        for mood, (low, high) in zones.items():
            if low is None and hr < high:
                return mood
            if high is None and hr >= low:
                return mood
            if low is not None and high is not None and low <= hr < high:
                return mood
        raise ValueError(hr)

    # -------------------------------------------------------------------------

    def send_new_mood_state(self, message: str) -> None:
        logger.info("Announcing mood: %s", message)
        self._sender.send_to_chat(message)

    # -------------------------------------------------------------------------

    def reset_state(self) -> None:
        self._hr_history.clear()
        self._current_mood = None
        self._pending_mood = None
        self._last_notified_bpm = None
