from collections.abc import Awaitable, Callable
from typing import Any

from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from webfluid import Fluid
from webfluid.core.lifecycle import RequestLifecycle

def _buffered(
    status: int, headers: list[tuple[bytes, bytes]], chunks: list[bytes]
) -> Response: ...

class RequestMiddleware:
    app: ASGIApp
    fluid: Fluid
    lifecycle: RequestLifecycle
    def __init__(
        self, app: ASGIApp, fluid: Fluid, request_lifecycle: RequestLifecycle
    ) -> None: ...
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None: ...
    async def _process(
        self, scope: Scope, receive: Receive,
        send: Send, lifecycle: RequestLifecycle
    ) -> None: ...

def add(fluid: Fluid, request_lifecycle: RequestLifecycle) -> None: ...
