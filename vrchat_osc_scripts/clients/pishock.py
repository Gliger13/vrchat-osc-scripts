"""Module contains PiShock client to interact with PiShock"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Final

import requests

from vrchat_osc_scripts.config import Config

logger = logging.getLogger(__name__)


class Operation(Enum):
    """Name of PiShock operation."""

    SHOCK = 0
    VIBRATE = 1
    BEEP = 2


class PiShockClient:
    """Client to send commands to the PiShock API."""

    API_URL: Final[str] = "https://do.pishock.com/api/apioperate"

    def __init__(self) -> None:
        """Initialize the client using creds from env vars"""
        if not any((Config.PISHOCK_USERNAME, Config.PISHOCK_API_KEY, Config.PISHOCK_CODE)):
            raise ValueError("One of PiShock credentials is not set in environment variables")
        self._last_shock_time: datetime | None = None

    def send_command(
        self,
        name: str,
        intensity: int,
        duration: int,
        operation: Operation,
    ) -> bool:
        """
        Send a command to the PiShock API.

        :param name: Name identifier for the command.
        :param intensity: Intensity level as a string (e.g., "6").
        :param duration: Duration of the shock (seconds as string).
        :param operation: Operation mode (e.g., "0").
            0 - Shock
            1 - Vibrate
            2 - Beep
        :return: True if the request was sent, otherwise False
        """
        payload = {
            "Username": Config.PISHOCK_USERNAME,
            "Name": name,
            "Code": Config.PISHOCK_CODE,
            "Intensity": intensity,
            "Duration": duration,
            "Apikey": Config.PISHOCK_API_KEY,
            "Op": operation.value,
        }
        if payload["Intensity"] > Config.MAX_SHOCK_INTENSITY_SAFE_GUARD:
            raise ValueError(f"SAFE GUARD PREVENTED INTENSITY HIGHER THAN {Config.MAX_SHOCK_INTENSITY_SAFE_GUARD}")
        headers = {"Content-Type": "application/json"}
        if self._last_shock_time is not None:
            time_since_last_shock = datetime.now() - self._last_shock_time
            if time_since_last_shock <= Config.SHOCK_COOLDOWN_TIME:
                logger.info(
                    f"PiShock command rejected, cool down is not done. "
                    f"Passed: {time_since_last_shock.total_seconds()}s"
                )
                return False

        logger.info(
            f"Sending PiShock command {name} with operation {operation.name}, and intensity {intensity}, "
            f"and duration {duration}"
        )
        self._last_shock_time = datetime.now()
        response = requests.post(self.API_URL, json=payload, headers=headers, timeout=30)
        logger.info(response.text)
        response.raise_for_status()
        return True
