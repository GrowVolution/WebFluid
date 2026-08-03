from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from fastapi import Request, Response, WebSocket

_proxy_client: httpx.AsyncClient | None
_SKIPPED_HEADERS: frozenset[str]

def proxy_client() -> httpx.AsyncClient: ...
def get_proxy(
    base_url: str, prefix: str = "", pass_prefix: bool = False,
    proxy_plugin: Callable[..., Awaitable[Any]] | None = None
) -> Callable[[Request, str], Awaitable[Response]]: ...
def get_websocket_proxy(
    base_url: str, prefix: str = "", pass_prefix: bool = False,
    proxy_plugin: Callable[..., Awaitable[Any]] | None = None
) -> Callable[[WebSocket, str], Awaitable[None]]: ...
def add_proxy(
    target: Any, base_url: str, prefix: str = "", pass_prefix: bool = False,
    proxy_plugin: Callable[..., Awaitable[Any]] | None = None
) -> None: ...
async def close_proxy_client() -> None: ...
