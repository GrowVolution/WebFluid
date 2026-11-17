from datetime import datetime, UTC
import asyncio, os, signal, uvicorn

from webfluid.core.constants import EXT_EVENTS
from webfluid.utils.logging import factory as log_factory

_SIGNALS = (signal.SIGINT, signal.SIGTERM) + (
    (signal.SIGBREAK,) if os.name == "nt" else ()
)


class Server:
    READINESS_INTERVAL = 0.01

    def __init__(self, fluid, lifecycle):
        self._server = None
        self._lifecycle = lifecycle
        self.app = fluid

    def _absorb_signals(self):
        for sig in _SIGNALS: signal.signal(sig, lambda *_: None)

    async def _started(self, serve):
        while not self._server.started:
            if serve.done(): return False
            await asyncio.sleep(self.READINESS_INTERVAL)
        return True

    def _announce(self, host, port):
        if not EXT_EVENTS: return

        from webfluid.core.ext import events
        from webfluid.extensions.events.main import EventBus

        payload = {
            "host": host,
            "port": port,
            "pid": os.getpid(),
            "started_at": datetime.now(UTC).isoformat()
        }
        try: events.trigger(EventBus.SERVER_RUNNING, payload)
        except Exception as e:
            log_factory.exception(e, f"Could not announce '{EventBus.SERVER_RUNNING}'.")

    async def _run_server(self):
        host = os.getenv("SERVER_HOST", "127.0.0.1")
        port = int(os.getenv("SERVER_PORT", "8000"))

        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            loop="asyncio",
            log_config=None,
            access_log=False,
            timeout_graceful_shutdown=5
        )

        self._absorb_signals()
        self._server = uvicorn.Server(config)

        log_factory.log(f"Server is listening on {host}:{port}.")
        serve = asyncio.create_task(self._server.serve())

        if await self._started(serve): self._announce(host, port)
        await serve

    async def _start(self):
        log_factory.start_session()

        try:
            await self._lifecycle.run_startup()
            await self._run_server()

        finally:
            await self._lifecycle.run_shutdown()
            log_factory.log("Server stopped.")

    def run(self): asyncio.run(self._start())
