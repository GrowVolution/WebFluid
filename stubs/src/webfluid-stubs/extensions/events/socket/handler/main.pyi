from fastapi import WebSocket
from typing import Any

from webfluid.extensions.events.events import Events
from webfluid.extensions.events.queries import Queries
from webfluid.extensions.events.socket.main import SocketManager

_KEYS: tuple[str, ...]

async def _send(ws: WebSocket, response: dict[str, Any]) -> None: ...
async def _receive(
    ws: WebSocket
) -> tuple[dict[str, Any] | None, str | None]: ...

class SocketHandler:
    _manager: SocketManager
    _events: Events
    _queries: Queries
    def __init__(
        self, socket_manager: SocketManager, events: Events, queries: Queries
    ) -> None: ...
    async def _dispatch(
        self, ws: WebSocket, sid: str, msg: dict[str, Any]
    ) -> None: ...
    async def _handle(self, ws: WebSocket) -> None: ...
    async def handle(self, ws: WebSocket) -> None: ...
