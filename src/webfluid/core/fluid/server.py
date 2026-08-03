import asyncio, signal, os, uvicorn

from webfluid.utils.logging import factory as log_factory


class Server:
    def __init__(self, fluid, lifecycle):
        self._loop = None
        self._server = None
        self._shutdown_flag = asyncio.Event()
        self._lifecycle = lifecycle
        self.app = fluid

        fluid.startup_hook(self._add_shutdown_handlers)

    def _add_shutdown_handlers(self):
        self._loop = asyncio.get_running_loop()
        if os.name == "nt":
            signal.signal(signal.SIGINT, self._handle_shutdown)
            signal.signal(signal.SIGBREAK, self._handle_shutdown)
            signal.signal(signal.SIGTERM, self._handle_shutdown)
        else:
            self._loop.add_signal_handler(signal.SIGINT, self._handle_shutdown)
            self._loop.add_signal_handler(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, *_):
        if self._shutdown_flag.is_set(): return
        self._loop.call_soon_threadsafe(self._shutdown_flag.set)

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

        self._server = uvicorn.Server(config)
        self._server.install_signal_handlers = False

        log_factory.log(f"Server is listening on {host}:{port}.")
        await self._server.serve()

    async def _start(self):
        log_factory.start_session()

        await self._lifecycle.run_startup()
        serve = asyncio.create_task(self._run_server())
        stop = asyncio.create_task(self._shutdown_flag.wait())

        try:
            await asyncio.wait(
                (serve, stop),
                return_when=asyncio.FIRST_COMPLETED
            )
            stop.cancel()

            if not serve.done() and self._server:
                self._server.should_exit = True
            await serve

        finally:
            await self._lifecycle.run_shutdown()
            log_factory.log("Server stopped.")

    def run(self): asyncio.run(self._start())
