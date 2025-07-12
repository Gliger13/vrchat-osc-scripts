import pytest
from datetime import datetime, timedelta, timezone

from vrchat_osc_scripts.handlers import heart_rate_chatbox_update_v3 as hrh

from vrchat_osc_scripts.handlers.heart_rate_chatbox_update_v3 import HeartRateChatBoxUpdateHandler


import pytest
from datetime import datetime, timedelta, timezone

class DummySender:
    def __init__(self):
        self.messages = []

    def send_to_chat(self, message):
        self.messages.append(message)


class DummyReceiver:
    """Placeholder – the handler only needs a receiver object for __init__."""


# ---------------------------------------------------------------------------
# Clock‑freezing fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def freeze_time(monkeypatch):
    """Freeze the handler's idea of *now* so tests can move time forward deterministically.

    We patch the *``datetime`` symbol* inside the handler module to a subclass that
    overrides ``now``.  Changing that override lets every call inside the
    production code return our synthetic timestamp.  We do **not** touch the
    global ``datetime`` used by the test code itself.
    """

    current_time = datetime(2025, 1, 1, tzinfo=timezone.utc)

    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: N802  (keeps signature of datetime.now)
            return current_time.astimezone(tz) if tz else current_time

    # Replace the symbol the handler imported at module import time
    monkeypatch.setattr(hrh, "datetime", _FrozenDateTime, raising=False)

    def _set(new_time: datetime):
        nonlocal current_time
        current_time = new_time

    return _set


# ---------------------------------------------------------------------------
# Handler fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def handler(freeze_time):
    sender = DummySender()
    receiver = DummyReceiver()
    return HeartRateChatBoxUpdateHandler(sender, receiver), sender, freeze_time


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NORMALISED = lambda bpm: bpm / 250.0  # noqa: E731 – tiny helper lambda

def last_message(sender):
    return sender.messages[-1] if sender.messages else None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_bucket_moods(handler):
    h, _, _ = handler
    zones = [
        (45, "♡ deep sleeping"),
        (55, "♡ sleeping"),
        (70, "♡ comfy"),
        (90, "♡ normal"),
        (120, "♡ active"),
        (150, "♡ intense"),
    ]
    for bpm, expected in zones:
        assert h._bucket_mood(bpm) == expected


def test_initial_mood_announcement(handler):
    h, sender, set_time = handler
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    set_time(base)
    h.on_parameter_changed("Normalised", NORMALISED(75))  # comfy
    assert sender.messages == ["♡ comfy"]


def test_invalid_hr_input(handler):
    h, sender, set_time = handler
    set_time(datetime(2025, 1, 1, tzinfo=timezone.utc))
    h.on_parameter_changed("Normalised", "bad")
    assert sender.messages == []


def test_stabilized_mood_change(handler):
    h, sender, set_time = handler
    dwell = h.STATE_STABILISATION_SEC

    base = datetime(2025, 1, 1, tzinfo=timezone.utc)
    set_time(base)
    h.on_parameter_changed("Normalised", NORMALISED(90))  # normal
    assert last_message(sender).startswith("♡ normal")

    # Feed "active" samples for < dwell seconds – no change expected
    for i in range(dwell - 5):
        set_time(base + timedelta(seconds=i + 1))
        h.on_parameter_changed("Normalised", NORMALISED(120))  # active candidate
    assert last_message(sender).startswith("♡ normal")

    # Now advance beyond dwell and keep sending active -> should flip
    for i in range(5):
        set_time(base + timedelta(seconds=dwell + i + 1))
        h.on_parameter_changed("Normalised", NORMALISED(122))

    assert last_message(sender).startswith("♡ active")


def test_sudden_jump_detection(handler):
    h, sender, set_time = handler
    dwell = h.STATE_STABILISATION_SEC

    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    set_time(t0)
    h.on_parameter_changed("Normalised", NORMALISED(85))  # establish normal

    # Big jump -> excited candidate
    set_time(t0 + timedelta(seconds=2))
    h.on_parameter_changed("Normalised", NORMALISED(105))

    assert last_message(sender).startswith("♡ normal")  # still debouncing

    # Keep HR high so the *next* sample also qualifies as excited
    set_time(t0 + timedelta(seconds=2 + dwell))
    h.on_parameter_changed("Normalised", NORMALISED(130))  # bigger jump maintains excited
    assert last_message(sender).startswith("♡ excited")


def test_sudden_drop_detection(handler):
    h, sender, set_time = handler
    dwell = h.STATE_STABILISATION_SEC

    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    set_time(t0)
    h.on_parameter_changed("Normalised", NORMALISED(110))  # active baseline

    # Sudden drop -> calming candidate
    set_time(t0 + timedelta(seconds=2))
    h.on_parameter_changed("Normalised", NORMALISED(85))
    assert last_message(sender).startswith("♡ active")

    # Keep HR low so the *next* sample still qualifies as calming
    set_time(t0 + timedelta(seconds=2 + dwell))
    h.on_parameter_changed("Normalised", NORMALISED(60))
    assert last_message(sender).startswith("♡ calming")


def test_significant_delta_message(handler):
    h, sender, set_time = handler
    set_time(datetime(2025, 1, 1, tzinfo=timezone.utc))

    h.on_parameter_changed("Normalised", NORMALISED(100))
    assert h._current_mood == "♡ normal"

    set_time(datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=1))
    h.on_parameter_changed("Normalised", NORMALISED(115))

    assert any("115" in msg for msg in sender.messages)


def test_reset_state(handler):
    h, _, _ = handler
    h._hr_history.append((datetime.now(timezone.utc), 100))
    h._current_mood = "♡ normal"
    h._pending_mood = ("♡ active", datetime.now(timezone.utc))
    h._last_notified_bpm = 115

    h.reset_state()

    assert not h._hr_history
    assert h._current_mood is None
    assert h._pending_mood is None
    assert h._last_notified_bpm is None
