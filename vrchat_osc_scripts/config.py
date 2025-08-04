"""Configuration module for OSC, VRChat, and Avatar."""

import os
from datetime import timedelta
from typing import Final

import dotenv


class Config:
    """Configuration constants for OSC, VRChat, and Avatar."""

    dotenv.load_dotenv()

    # IP address used to receive OSC messages from VRChat
    VRCHAT_OSC_RECEIVE_IP: Final[str] = os.getenv("VRCHAT_OSC_RECEIVE_IP", "127.0.0.1")

    # Port on which the local app receives OSC messages (sent by VRChat)
    VRCHAT_OSC_RECEIVE_PORT: Final[int] = int(os.getenv("VRCHAT_OSC_RECEIVE_PORT", 9001))

    # IP address used to send OSC messages to VRChat
    VRCHAT_OSC_SEND_IP: Final[str] = os.getenv("VRCHAT_OSC_SEND_IP", "127.0.0.1")

    # Port on which VRChat listens for incoming OSC messages
    VRCHAT_OSC_SEND_PORT: Final[int] = int(os.getenv("VRCHAT_OSC_SEND_PORT", 9000))

    PISHOCK_USERNAME = os.getenv("PISHOCK_USERNAME", None)
    PISHOCK_API_KEY = os.getenv("PISHOCK_API_KEY", None)
    PISHOCK_CODE = os.getenv("PISHOCK_CODE", None)

    AVATAR_TAIL_PARAMETER_NAME: Final[str] = os.getenv("AVATAR_TAIL_PARAMETER_NAME", "tail")
    SHOCK_INTENSITY_ON_TAIL_GRAB: Final[int] = int(os.getenv("SHOCK_INTENSITY_ON_TAIL_GRAB", 1))
    SHOCK_DURATION_ON_TAIL_GRAB: Final[int] = int(os.getenv("SHOCK_DURATION_ON_TAIL_GRAB", 1))
    SHOCK_COOLDOWN_TIME: Final[timedelta] = timedelta(seconds=int(os.getenv("SHOCK_COOLDOWN_TIME", 30)))
    MAX_SHOCK_INTENSITY_SAFE_GUARD: Final[int] = int(os.getenv("MAX_SHOCK_INTENSITY_SAFE_GUARD", 80))
    SHOCK_MESSAGE = os.getenv("SHOCK_MESSAGE", "⚡️")
