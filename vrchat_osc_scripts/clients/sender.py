"""VRChat OSC Sender module.

Defines VRChatOSCSender to send OSC parameter updates to VRChat.
"""

import logging
from datetime import timedelta
from typing import Optional

from pythonosc.udp_client import SimpleUDPClient

from vrchat_osc_scripts.config import Config

logger = logging.getLogger(__name__)


class VRChatOSCSender:
    """OSC sender to transmit parameters to VRChat."""

    def __init__(self, ip: str = Config.VRCHAT_OSC_SEND_IP, port: int = Config.VRCHAT_OSC_SEND_PORT) -> None:
        """Initialize the OSC sender.

        :param ip: IP address of the OSC server (VRChat).
        :param port: Port for sending OSC messages.
        """
        self.client = SimpleUDPClient(ip, port)

    def send_parameter(self, parameter: str, value: float | int | bool | str) -> None:
        """Send a parameter value to VRChat.

        :param parameter: Name of the parameter.
        :param value: Value to send (float, int, bool, or str).
        """
        logger.info(f"Sending: {parameter} = {value}")
        self.client.send_message(parameter, value)

    def send_to_chat(self, text: str, time_to_clear: Optional[timedelta] = None) -> None:
        """Send the given text to VRChat textbox."""
        self.send_parameter("/chatbox/input", text)
        # self.send_parameter("/chatbox/input", text)