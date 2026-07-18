from typing import Any

from webfluid.extensions.events.events import Events
from webfluid.extensions.events.socket.main import SocketManager

def add_listener(
    socket_manager: SocketManager, events: Events, sid: str,
    msg: dict[str, Any], res: dict[str, Any]
) -> dict[str, Any] | None: ...
