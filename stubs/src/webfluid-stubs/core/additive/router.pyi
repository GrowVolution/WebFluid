from collections.abc import Callable
from typing import Any

from fastapi import APIRouter

class Router(APIRouter):
    _http_middleware: list[Callable[..., Any]]
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def http_middleware(self, fn: Callable[..., Any]) -> Callable[..., Any]: ...
    def _wrapped(self, endpoint: Callable[..., Any]) -> Callable[..., Any]: ...
    def add_api_route(
        self, path: str, endpoint: Callable[..., Any], **kwargs: Any
    ) -> None: ...
    def add_api_websocket_route(
        self, path: str, endpoint: Callable[..., Any],
        name: str | None = None, **kwargs: Any
    ) -> None: ...
