"""VRChat OSC Receiver module.

Defines VRChatOSCReceiver to listen for OSC parameter changes from VRChat,
manage registered handlers, and notify them on parameter updates.
"""

import logging
from typing import Any

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer

from vrchat_osc_scripts.config import Config


logger = logging.getLogger(__name__)


class VRChatOSCReceiver:
    """OSC receiver for VRChat parameters.

    Listens for incoming OSC messages from VRChat on configured IP and port,
    tracks parameter states, and dispatches updates to registered handlers.
    """

    def __init__(
        self,
        ip: str = Config.VRCHAT_OSC_RECEIVE_IP,
        port: int = Config.VRCHAT_OSC_RECEIVE_PORT,
    ) -> None:
        """Initialize the OSC receiver.

        :param ip: IP address to listen on for incoming OSC messages.
        :param port: Port to listen on for incoming OSC messages.
        """
        self.ip = ip
        self.port = port
        self.dispatcher = Dispatcher()
        self.dispatcher.map("/avatar/parameters/*", self._handle_parameter)

        self.parameters: dict[str, Any] = {}
        self.handlers: list["BaseHandler"] = []

        self.server = BlockingOSCUDPServer((self.ip, self.port), self.dispatcher)

    def _handle_parameter(self, address: str, *args: Any) -> None:
        """Handle incoming OSC parameter messages.

        :param address: OSC address pattern of the message.
        :param args: OSC message arguments (parameter values).
        """
        param_name = address.split("/")[-1]
        value = args[0] if args else None

        old_value = self.parameters.get(param_name)
        self.parameters[param_name] = value

        if old_value != value:
            logger.debug(f"Parameter changed: {param_name} = {value}")
            for handler in self.handlers:
                try:
                    handler.on_parameter_changed(param_name, value)
                except Exception as e:
                    logger.error(
                        f"Error in handler {handler.__class__.__name__} for '{param_name}': {e}"
                    )

    def add_handler(self, handler: "BaseHandler") -> None:
        """Register a new handler to receive parameter updates.

        :param handler: Instance of BaseHandler or subclass to register.
        """
        self.handlers.append(handler)
        logger.info(f"Registered handler: {handler.__class__.__name__}")

    def serve_forever(self) -> None:
        """Start the OSC server to listen for incoming messages indefinitely."""
        logger.info("Starting OSC server...")
        self.server.serve_forever()

    def get_parameters(self) -> dict[str, Any]:
        """Get a copy of the current parameters dictionary.

        :return: A dictionary mapping parameter names to their current values.
        """
        return dict(self.parameters)
