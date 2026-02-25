from socketio import ASGIApp
import os, uvicorn, asyncio

from webfluid import version
from webfluid.base import App
from webfluid.core.api import ApiLiquid
from webfluid.core.app import AppLiquid
from webfluid.core.ext import socket, scheduler, cache, mail, jwt
from webfluid.additives import register_additives
from webfluid.utils import enabled, disable_uvicorn_logging
from webfluid.utils.config import init_configs


class Fluid(App):
    def __init__(self, import_name: str):
        super().__init__(import_name)
        init_configs(self)

        self.api = ApiLiquid(self)
        self.app = AppLiquid(import_name)
        self.app.setup(self)

        if enabled("EXT_SCHEDULER"):
            self.startup_hook(scheduler.start)

        if enabled("EXT_CACHE"): cache.init_fluid(self)
        if enabled("EXT_MAIL"): mail.init_fluid(self)
        if enabled("EXT_JWT"): jwt.init_fluid(self)

        self.startup_hook(self._prepare_api)
        self.startup_hook(
            lambda: register_additives(self)
        )

        self._asgi_app = None

    def __repr__(self) -> str:
        return f"<WebFluid {version()}>"

    def _prepare_api(self):
        self.api.mount("/app", self.app, "app")
        self.api.mount("/static", self.app_static, "static")
        self.api.mount("/wf-static", self.framework_static, "wf_static")

    async def _run_server(self):
        config = uvicorn.Config(
            self.asgi_app,
            host="0.0.0.0",
            port=int(os.getenv("SERVER_PORT", "5000"))
        )
        server = uvicorn.Server(config)
        disable_uvicorn_logging()
        await server.serve()

    @property
    def asgi_app(self) -> ASGIApp | ApiLiquid:
        if self._asgi_app is not None: return self._asgi_app

        if enabled("EXT_SOCKET"):
            self._asgi_app = ASGIApp(socket, other_asgi_app=self.api.asgi)
        else:
            self._asgi_app = self.api.asgi

        return self._asgi_app

    async def start(self):
        await self._startup()
        serve = asyncio.create_task(self._run_server())
        await self._shutdown_flag.wait()
        await self._shutdown()

        try:
            serve.cancel()
            await serve
        except asyncio.CancelledError:
            pass
