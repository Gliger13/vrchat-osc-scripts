"""VRChat OSC Sender module.

Defines VRChatOSCSender to send OSC parameter updates to VRChat.
"""

import logging

from pythonosc.osc_message_builder import ArgValue
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

    def send_parameter(self, parameter: str, values: ArgValue) -> None:
        """Send a parameter value to VRChat.

        :param parameter: Name of the parameter.
        :param values: Value to send (float, int, bool, or str, or list of those values).
        """
        logger.info(f"Sending: {parameter} = {values}")
        self.client.send_message(parameter, values)

    def send_to_chat(
        self,
        text: str,
        to_send_immediately: bool = True,
        to_send_notification: bool = False,
    ) -> None:
        """Send the given text to VRChat textbox."""
        self.send_parameter("/chatbox/input", values=[text, to_send_immediately, to_send_notification])
