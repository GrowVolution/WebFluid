from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from jinja2 import Environment, ChoiceLoader, PrefixLoader, FileSystemLoader
from markupsafe import Markup
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from pathlib import Path
from datetime import datetime, UTC
from typing import Callable
import os, asyncio, uvicorn, signal

from webfluid.core.config import Config, init_configs, build_config
from webfluid.core.context import FluidContext
from webfluid.core.constants import (
    FRAMEWORK_ROOT,
    APP_STATIC, WF_STATIC,
    TAILWIND, PROCESSING,
    EXT_SCHEDULING, EXT_SQLALCHEMY,
    EXT_BABEL, EXT_CACHE,
    EXT_MAIL, EXT_JWT
)
from webfluid.core.ext import scheduler, db, babel, cache, mail, jwt
from webfluid.additives import register_additives
from webfluid.surface.frontend import Frontend, validate_config
from webfluid.surface.wf_tailwind import generate_tailwind_css
from webfluid.extensions.utils.babel import get_locale, fake_t, fake_tn
from webfluid.utils import (get_root_path, safe_string, safe_execute,
                            required_arg_count, close_proxy_client)
from webfluid.utils.logging import factory as log_factory
from webfluid.exceptions import EventHookException, ProcessorException


class Fluid(FastAPI):
    def __init__(self, import_name: str):
        self.name = safe_string(os.getenv("APP_NAME", import_name)).lower()

        self.app_root = Path(get_root_path(import_name)).resolve()
        self.additive_root = self.app_root / "additives"

        init_configs(self)
        self.config = Config()
        self.config.from_object(build_config())
        super().__init__(**self.config.get("APP_CONFIG", {}))

        static_path = "fluid/static"
        self.app_static = StaticFiles(
            directory=(self.app_root / static_path)
        )
        self.framework_static = StaticFiles(
            directory=(FRAMEWORK_ROOT / static_path)
        )

        self.jinja_env = Environment(enable_async=True)
        template_path = "fluid/templates"
        app_templates = FileSystemLoader(self.app_root / template_path)
        framework_templates = FileSystemLoader(FRAMEWORK_ROOT / template_path)
        self.app_loader = ChoiceLoader([
            app_templates, PrefixLoader({ "app": app_templates })
        ])
        self.framework_loader = ChoiceLoader([
            framework_templates, PrefixLoader({ "framework": framework_templates })
        ])
        self._context_processors = []
        self._request_processors = {
            "before": [],
            "after": []
        }
        self._hooks = {
            "startup": [],
            "shutdown": []
        }
        self._startup_lock = False
        self._shutdown_lock = False

        self.jinja_context = {}
        if "APP_FRONTEND" in self.config and self.config["APP_FRONTEND"] is not None:
            result = validate_config(self.config["APP_FRONTEND"])
            if not result[0]:
                raise ValueError(f"Invalid frontend configuration: {result[1]}")
            self.frontend = Frontend()
            self.startup_hook(lambda: self.frontend.cover_fluid(self))
            self.jinja_context["frontend"] = self.frontend.include

        if self.config.get("RATELIMIT_ENABLED", True):
            self.state.limiter = Limiter(
                key_func=get_remote_address,
                default_limits=self.config.get(
                    "RATELIMIT_DEFAULT", ["500/day", "100/hour"]
                ),
                storage_uri=self.config.get("RATELIMIT_STORAGE_URI", "redis://localhost:6379/1"),
            )
            self.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        @self.middleware("http")
        async def middleware(
                request: Request, call_next: Callable
        ) -> Response:
            async with FluidContext(self, request):
                for processor in self._request_processors["before"]:
                    response = await safe_execute(processor, ProcessorException, request)
                    if response is not None: return response
                response = await call_next(request)
                for processor in reversed(self._request_processors["after"]):
                    response = await safe_execute(processor, ProcessorException, request, response)
                return response

        if EXT_SCHEDULING: self.startup_hook(scheduler.start)
        if EXT_SQLALCHEMY: db.expand_fluid(self)
        if EXT_BABEL: babel.expand_fluid(self)
        if EXT_CACHE: cache.expand_fluid(self)
        if EXT_MAIL: mail.expand_fluid(self)
        if EXT_JWT: jwt.expand_fluid(self)

        if TAILWIND:
            self.startup_hook(lambda: generate_tailwind_css(self))
            self.jinja_context["wf_tailwind"] = Markup('<link rel="stylesheet" href="/wf-static/css/tailwind.css">')

        self.startup_hook(
            lambda: register_additives(self)
        )
        self.startup_hook(self._prepare)
        Frontend.prepare(self)

        if PROCESSING:
            if not EXT_BABEL:
                self.jinja_env.add_extension("jinja2.ext.i18n")
                self.jinja_env.install_gettext_callables(
                    fake_t, fake_tn, newstyle=True
                )
                lang = lambda: "en"
            else:
                lang = get_locale

            self.context_processor(lambda: {
                **self.jinja_context,
                "LANG": lang(),
                "YEAR": datetime.now(UTC).year
            })

            def before_request(r: Request):
                agent = r.headers.get("user-agent", "unknown")
                log_factory.log(
                    f"[Request] {r.method} {r.url.path} from {r.client.host} ({agent})"
                )

            self.before_request(before_request)

            async def after_request(_, response: Response):
                if response.status_code == 404:
                    return HTMLResponse(
                        await self.render("404.html"),
                        status_code=404
                    )
                return response

            self.after_request(after_request)

            async def exception_handler(request: Request, exc: Exception):
                log_factory.exception(exc, f"{request.method} {request.url.path}")
                return HTMLResponse(
                    await self.render("500.html", error=str(exc)),
                    status_code=500
                )

            self.add_exception_handler(Exception, exception_handler)

        self._asgi_app = None
        self._server = None
        self._shutdown_flag = asyncio.Event()

        def add_shutdown_handlers():
            if os.name == "nt":
                signal.signal(signal.SIGINT, self._handle_shutdown)
                signal.signal(signal.SIGTERM, self._handle_shutdown)
            else:
                loop = asyncio.get_running_loop()
                loop.add_signal_handler(signal.SIGINT, self._handle_shutdown)
                loop.add_signal_handler(signal.SIGTERM, self._handle_shutdown)

        self.startup_hook(add_shutdown_handlers)
        self.shutdown_hook(close_proxy_client)

    def __repr__(self) -> str:
        from webfluid import version
        return f"<WebFluid {version()}>"

    def _prepare(self):
        self.mount(APP_STATIC, self.app_static, "static")
        self.mount(WF_STATIC, self.framework_static, "wf_static")

    async def _startup(self):
        self._startup_lock = True

        log_factory.log("Running startup hooks...")
        for hook in self._hooks["startup"]:
            await safe_execute(hook, EventHookException)

    async def _shutdown(self):
        self._shutdown_lock = True

        log_factory.log("Running shutdown hooks...")
        for hook in reversed(self._hooks["shutdown"]):
            await safe_execute(hook, EventHookException)

    async def _run_server(self):
        host = os.getenv("SERVER_HOST", "127.0.0.1")
        port = int(os.getenv("SERVER_PORT", "8000"))

        config = uvicorn.Config(
            self.asgi_app,
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

    def _handle_shutdown(self, *_):
        if self._shutdown_flag.is_set(): return
        self._shutdown_flag.set()

    def startup_hook(self, fn: Callable) -> Callable:
        if self._startup_lock:
            raise RuntimeError("Startup hooks cannot be added after the server was started.")

        if required_arg_count(fn) > 0:
            raise TypeError("Startup hooks must not receive non optional arguments.")

        self._hooks["startup"].append(fn)
        return fn

    def shutdown_hook(self, fn: Callable) -> Callable:
        if self._shutdown_lock:
            raise RuntimeError("Shutdown hooks cannot be added after the server was stopped.")

        if required_arg_count(fn) > 0:
            raise TypeError("Shutdown hooks must not receive non optional arguments.")

        self._hooks["shutdown"].append(fn)
        return fn

    def context_processor(self, fn: Callable) -> Callable:
        if required_arg_count(fn) > 0:
            raise TypeError("Context processors must not receive non optional arguments.")
        self._context_processors.append(fn)
        return fn

    def before_request(self, fn: Callable) -> Callable:
        if required_arg_count(fn) != 1:
            raise TypeError("Before request processors must receive exactly one argument (request).")
        self._request_processors["before"].append(fn)
        return fn

    def after_request(self, fn: Callable) -> Callable:
        if required_arg_count(fn) != 2:
            raise TypeError("After request processors must receive exactly one argument (request, response).")
        self._request_processors["after"].append(fn)
        return fn

    async def render(self, template: str, **ctx) -> str:
        for processor in self._context_processors:
            result = await safe_execute(processor, ProcessorException)
            if not isinstance(result, dict): continue
            ctx = result | ctx
        return await self.jinja_env.get_template(template).render_async(**ctx)

    async def start(self):
        log_factory.start_session()

        await self._startup()
        serve = asyncio.create_task(self._run_server())
        await self._shutdown_flag.wait()

        if self._server:
            self._server.should_exit = True
            await serve

        await self._shutdown()
        log_factory.log("Server stopped.")

    def mix(self): asyncio.run(self.start())

    @property
    def asgi_app(self) -> Fluid | ProxyHeadersMiddleware:
        if self._asgi_app is not None: return self._asgi_app

        if self.config.get("PROXY_FIX", False):
            self._asgi_app = ProxyHeadersMiddleware(self)
        else:
            self._asgi_app = self

        return self._asgi_app

    @property
    def limit(self) -> Callable:
        if self.config.get("RATELIMIT_ENABLED", True):
            return self.state.limiter.limit
        return lambda *_, **__: lambda fn: fn
