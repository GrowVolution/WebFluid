from collections.abc import Callable
from typing import Any

import httpx

from webfluid import Fluid, Additive

_proxy_client: httpx.AsyncClient

def get_proxy(
    base_url: str, prefix: str = "", pass_prefix: bool = False,
    proxy_plugin: Callable[..., Any] | None = None
) -> Callable[..., Any]: ...
def get_websocket_proxy(
    base_url: str, prefix: str = "", pass_prefix: bool = False,
    proxy_plugin: Callable[..., Any] | None = None
) -> Callable[..., Any]: ...
def add_proxy(
    target: Fluid | Additive, base_url: str, prefix: str = "",
    pass_prefix: bool = False, proxy_plugin: Callable[..., Any] | None = None
) -> None: ...
async def close_proxy_client() -> None: ...
