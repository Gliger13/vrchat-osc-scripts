"""Main entry point for the VRChat OSC script.

This module initializes the OSC sender and receiver, registers
parameter handlers, and starts the OSC server to listen for parameter changes.
"""

import logging

from vrchat_osc_scripts.clients.pishock import PiShockClient
from vrchat_osc_scripts.clients.receiver import VRChatOSCReceiver
from vrchat_osc_scripts.clients.sender import VRChatOSCSender
from vrchat_osc_scripts.handlers.heart_rate_chatbox_update_v3 import HeartRateChatBoxUpdateHandler
from vrchat_osc_scripts.handlers.shock_on_tail_grab import ShockOnTailGrabHandler
from vrchat_osc_scripts.tools.logger import setup_logging

logger = logging.getLogger(__name__)

def main() -> None:
    """Set up OSC sender and receiver, register handlers, and run the OSC server."""
    setup_logging(level=logging.DEBUG)
    sender = VRChatOSCSender()
    receiver = VRChatOSCReceiver()
    pishock_client = PiShockClient()

    receiver.add_handler(ShockOnTailGrabHandler(sender, receiver, pishock_client))
    # receiver.add_handler(HeartRateChatBoxUpdateHandler(sender, receiver))

    try:
        receiver.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")


if __name__ == "__main__":
    main()
