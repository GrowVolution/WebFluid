from fastapi import WebSocket

from webfluid.extensions.babel.babel.main import Babel


class Socket:
    _api_whitelist: set[str]
    babel: Babel
    def __init__(self, babel: Babel) -> None: ...
    async def _handle(self, ws: WebSocket) -> None: ...
    async def endpoint(self, ws: WebSocket) -> None: ...
