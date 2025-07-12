"""ShockOnTailGrubHandler module.

Defines a handler that reacts to specific VRChat OSC parameter changes.
"""
import logging
from typing import Any

from vrchat_osc_scripts.clients.pishock import PiShockClient, Operation
from vrchat_osc_scripts.clients.receiver import VRChatOSCReceiver
from vrchat_osc_scripts.clients.sender import VRChatOSCSender
from vrchat_osc_scripts.config import Config
from vrchat_osc_scripts.handlers.base import BaseHandler

logger = logging.getLogger(__name__)


class ShockOnTailGrabHandler(BaseHandler):
    """Handle tail‑grab events and trigger PiShock feedback.

    This handler monitors the avatar parameter that signals when the tail is
    grabbed.  When the parameter transitions from *not grabbed* to *grabbed*
    it calls the PiShock API to deliver a shock with the configured client.
    """

    def __init__(
        self,
        sender: VRChatOSCSender,
        receiver: VRChatOSCReceiver,
        pishock_client: PiShockClient,
    ) -> None:
        """Create a new tail-grab handler.

        :param sender: OSC client for sending responses back to VRChat.
        :param receiver: OSC receiver providing current avatar parameters.
        :param pishock_client: HTTP client for communicating with PiShock.
        """
        super().__init__(sender, receiver)
        self._pishock_client = pishock_client
        self._is_tail_grabbed: bool | None = None

    def on_parameter_changed(self, parameter: str, value: Any) -> None:
        """Handle changes to VRChat OSC parameters.

        Performs custom logic when the tracked parameter changes.

        :param parameter: The name of the changed parameter.
        :param value: The new value of the parameter.
        """
        if parameter == f"{Config.AVATAR_TAIL_PARAMETER_NAME}_IsGrabbed":
            logger.info(f"Tracked parameter changed: {parameter} = {value}")
            self._is_tail_grabbed = value
            if not self._is_tail_grabbed:
                self.send_shock()

    def send_shock(self) -> None:
        """Send a shock using the PiShock client and notify VRChat via OSC chat.

        If the PiShock API call is successful, a ⚡️ emoji is sent to the VRChat
        chat to indicate that a shock was triggered.
        """
        is_was_send = self._pishock_client.send_command(
            name="Shock From Tail Grab",
            intensity=1,
            duration=1,
            operation=Operation.SHOCK,
        )
        if is_was_send:
            self._sender.send_to_chat("⚡️")
