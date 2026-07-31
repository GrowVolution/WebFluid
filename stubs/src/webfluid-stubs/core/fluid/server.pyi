import asyncio
from asyncio import AbstractEventLoop
from typing import Any

import uvicorn

from webfluid import Fluid
from webfluid.core.lifecycle import FluidLifecycle

class Server:
    _loop: AbstractEventLoop | None
    _server: uvicorn.Server | None
    _shutdown_flag: asyncio.Event
    _lifecycle: FluidLifecycle
    app: Fluid
    def __init__(self, fluid: Fluid, lifecycle: FluidLifecycle) -> None: ...
    def _add_shutdown_handlers(self) -> None: ...
    def _handle_shutdown(self, *_: Any) -> None: ...
    async def _run_server(self) -> None: ...
    async def _start(self) -> None: ...
    def run(self) -> None: ...
