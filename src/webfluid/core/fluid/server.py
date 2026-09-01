import asyncio, signal, os, uvicorn

from webfluid.utils.logging import factory as log_factory

_SIGNALS = (signal.SIGINT, signal.SIGTERM) + (
    (signal.SIGBREAK,) if os.name == "nt" else ()
)


class Server:
    def __init__(self, fluid, lifecycle):
        self._server = None
        self._lifecycle = lifecycle
        self.app = fluid

    def _absorb_signals(self):
        for sig in _SIGNALS: signal.signal(sig, lambda *_: None)

    async def _run_server(self):
        host = os.getenv("SERVER_HOST", "127.0.0.1")
        port = int(os.getenv("SERVER_PORT", "8000"))

        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            loop="asyncio",
            log_config=None,
            access_log=False
        )

        self._absorb_signals()
        self._server = uvicorn.Server(config)

        log_factory.log(f"Server is listening on {host}:{port}.")
        await self._server.serve()

    async def _start(self):
        log_factory.start_session()

        try:
            await self._lifecycle.run_startup()
            await self._run_server()

        finally:
            await self._lifecycle.run_shutdown()
            log_factory.log("Server stopped.")

    def run(self): asyncio.run(self._start())
