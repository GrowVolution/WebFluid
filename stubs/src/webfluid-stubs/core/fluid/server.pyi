import signal

import uvicorn

from webfluid import Fluid
from webfluid.core.lifecycle import FluidLifecycle

_SIGNALS: tuple[signal.Signals, ...]

class Server:
    _server: uvicorn.Server | None
    _lifecycle: FluidLifecycle
    app: Fluid
    def __init__(self, fluid: Fluid, lifecycle: FluidLifecycle) -> None: ...
    def _absorb_signals(self) -> None: ...
    async def _run_server(self) -> None: ...
    async def _start(self) -> None: ...
    def run(self) -> None: ...
