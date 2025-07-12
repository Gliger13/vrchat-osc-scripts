
import logging
import statistics
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Deque, List, Tuple

from vrchat_osc_scripts.clients.receiver import VRChatOSCReceiver
from vrchat_osc_scripts.clients.sender import VRChatOSCSender
from vrchat_osc_scripts.handlers.base import BaseHandler

logger = logging.getLogger(__name__)


class HeartRateChatBoxUpdateHandler(BaseHandler):
    HISTORY_SIZE: int = 180             # Max samples in history (~3 min at 1 Hz)
    BASELINE_WINDOW_SEC: int = 30       # Rolling baseline window

    # Sudden change thresholds tuned per your request
    SUDDEN_JUMP_BPM: int = 18
    SUDDEN_JUMP_WINDOW_SEC: int = 30
    SUDDEN_DROP_BPM: int = 18
    SUDDEN_DROP_WINDOW_SEC: int = 30

    SIGNIFICANT_DELTA_BPM: int = 12    # Notify on delta regardless of mood change

    def __init__(
        self,
        sender: VRChatOSCSender,
        receiver: VRChatOSCReceiver,
    ):
        super().__init__(sender, receiver)
        self._hr_history: Deque[Tuple[datetime, float]] = deque(maxlen=self.HISTORY_SIZE)
        self._prev_mood: str | None = None

    def on_parameter_changed(self, parameter, hr) -> None:
        if parameter != "Normalised":
            return
        hr = hr * 250
        logger.info(f"Tracked parameter changed: {parameter} = {hr}")

        if hr is None:
            return

        try:
            hr = float(hr)
        except (TypeError, ValueError):
            logger.warning("Invalid heart rate value: %s", hr)
            return

        now = datetime.now(timezone.utc)
        self._hr_history.append((now, hr))

        baseline = self._compute_baseline(now, exclude_latest=True)

        last_sample = self._hr_history[-2] if len(self._hr_history) >= 2 else None
        last_hr = last_sample[1] if last_sample else None
        last_t = last_sample[0] if last_sample else None

        new_mood = self._derive_mood(hr, baseline, last_hr, last_t, now)

        significant_delta = (
            last_hr is not None and abs(hr - last_hr) >= self.SIGNIFICANT_DELTA_BPM
        )

        if significant_delta or new_mood != self._prev_mood:
            if last_hr is not None:
                message = f"{new_mood} ({int(last_hr)} -> {int(hr)})"
            else:
                message = new_mood
            self.send_new_mood_state(message)

        self._prev_mood = new_mood

    def _compute_baseline(self, now: datetime, *, exclude_latest: bool) -> float | None:
        cutoff = now - timedelta(seconds=self.BASELINE_WINDOW_SEC)
        samples: List[float] = []

        iter_len = len(self._hr_history) - (1 if exclude_latest else 0)
        for ts, bpm in list(self._hr_history)[:iter_len]:
            if ts >= cutoff:
                samples.append(bpm)

        return statistics.median(samples) if samples else None

    def _derive_mood(
        self,
        hr: float,
        baseline: float | None,
        last_hr: float | None,
        last_ts: datetime | None,
        now: datetime,
    ) -> str:
        if last_hr is not None and last_ts is not None:
            dt = (now - last_ts).total_seconds()
            if hr - last_hr >= self.SUDDEN_JUMP_BPM and dt <= self.SUDDEN_JUMP_WINDOW_SEC:
                return f"♡ excited"
            if last_hr - hr >= self.SUDDEN_DROP_BPM and dt <= self.SUDDEN_DROP_WINDOW_SEC:
                return f"♡ calming"

        if baseline is not None:
            delta = hr - baseline
            if delta >= self.SUDDEN_JUMP_BPM:
                return f"♡ excited"
            if delta <= -self.SUDDEN_DROP_BPM:
                return f"♡ calming"

        return self._bucket_mood(hr)

    def _bucket_mood(self, hr: float) -> str:
        zones = {
            "♡ deep sleeping": (None, 50),
            "♡ sleeping": (51, 60),
            "♡ comfy": (60, 79),
            "♡ normal": (80, 110),
            "♡ active": (110, 135),
            "♡ intense": (140, None),
        }
        for mood, (low, high) in zones.items():
            if low is None and hr < high:
                return mood
            if high is None and hr >= low:
                return mood
            if low is not None and high is not None and low <= hr < high:
                return mood
        raise ValueError(hr)

    def send_new_mood_state(self, message):
        self._sender.send_to_chat(message)

    def reset_state(self) -> None:
        self._hr_history.clear()
        self._prev_mood = None
