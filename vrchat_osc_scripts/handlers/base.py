"""Base handler abstraction for VRChat OSC events."""

from abc import ABCMeta, abstractmethod
from typing import Any

from vrchat_osc_scripts.clients.receiver import VRChatOSCReceiver
from vrchat_osc_scripts.clients.sender import VRChatOSCSender


class BaseHandler(metaclass=ABCMeta):
    """Abstract base class for VRChat OSC parameter handlers.

    Subclasses receive both an OSC sender and receiver so they can read the
    current parameter state and send new OSC messages in response to changes.
    """

    def __init__(self, sender: VRChatOSCSender, receiver: VRChatOSCReceiver) -> None:
        """Create a new handler.

        :param sender: OSC client used to transmit messages back to VRChat.
        :param receiver: OSC receiver that supplies access to current parameters.
        """
        self._sender = sender
        self._receiver = receiver

    @abstractmethod
    def on_parameter_changed(self, parameter: str, value: Any) -> None:
        """React to a single OSC parameter change.

        Subclasses must override this method to implement their own behaviour
        when a parameter update is received.

        :param parameter: The OSC parameter name, e.g. ``"GestureLeft"``.
        :param value: The new value of the parameter.
        """
