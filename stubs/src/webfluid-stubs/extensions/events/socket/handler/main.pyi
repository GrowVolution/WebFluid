import asyncio
from typing import Any

from fastapi import WebSocket

from webfluid.extensions.events.events import Events
from webfluid.extensions.events.queries import Queries
from webfluid.extensions.events.socket.main import SocketManager

async def _send(ws: WebSocket, response: dict[str, Any]) -> None: ...

class SocketHandler:
    _manager: SocketManager
    _events: Events
    _queries: Queries
    def __init__(
        self, socket_manager: SocketManager, events: Events, queries: Queries
    ) -> None: ...
    async def _handle(self, ws: WebSocket) -> None: ...
    def handle(self, ws: WebSocket) -> asyncio.Task[None]: ...
