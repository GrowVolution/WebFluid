from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from jinja2 import Environment, ChoiceLoader, PrefixLoader, FileSystemLoader
from markupsafe import Markup
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from pathlib import Path
from functools import wraps
from importlib import import_module
from typing import TYPE_CHECKING, Callable
import os, uvicorn, asyncio, signal, weakref

from webfluid import version
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
from webfluid.utils import (
    disable_uvicorn_logging, get_root_path,
    safe_string, safe_execute, required_arg_count
)
from webfluid.exceptions import EventHookException, ProcessorException

if TYPE_CHECKING:
    from types import FrameType


def _on_init(__init__: Callable) -> Callable:
    @wraps(__init__)
    def wrapper(import_name: str):
        for hook in Fluid._object_hooks["before_construction"]:
            hook()
        return __init__(import_name)
    return wrapper


class Fluid(FastAPI):
    _object_hooks = {
        "before_construction": [],
        "after_deconstruction": []
    }

    @_on_init
    def __init__(self, import_name: str):
        self.name = safe_string(os.getenv("APP_NAME", import_name)).lower()

        init_configs(self)
        self.config = Config()
        self.config.from_object(build_config())

        self.app_root = Path(get_root_path(import_name)).resolve()
        self.additive_root = self.app_root / "additives"

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

        jinja_context = {}
        if "APP_FRONTEND" in self.config and self.config["APP_FRONTEND"] is not None:
            result = validate_config(self.config["APP_FRONTEND"])
            if not result[0]:
                raise ValueError(f"Invalid frontend configuration: {result[1]}")
            self.frontend = Frontend()
            self.startup_hook(lambda: self.frontend.cover_fluid(self))
            jinja_context["frontend"] = self.frontend.include

        if self.config.get("RATELIMIT_ENABLED", True):
            self.state.limiter = Limiter(
                key_func=get_remote_address,
                default_limits=self.config.get(
                    "RATELIMIT_DEFAULT", ["500/day", "100/hour"]
                ),
                storage_uri=self.config.get("RATELIMIT_STORAGE_URI", "redis://localhost:6379/1"),
            )
            self.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        async def middleware(
                request: Request, call_next: Callable
        ) -> Response:
            async with FluidContext(self, request):
                for processor in self._request_processors["before"]:
                    response = await safe_execute(processor, ProcessorException, request)
                    if response is not None: return response
                response = await call_next(request)
                for processor in reversed(self._request_processors["after"]):
                    response = await safe_execute(processor, ProcessorException, response)
                return response

        self.middleware("http")(middleware)

        if EXT_SCHEDULING: self.startup_hook(scheduler.start)
        if EXT_SQLALCHEMY: db.expand_fluid(self)
        if EXT_BABEL: babel.expand_fluid(self)
        if EXT_CACHE: cache.expand_fluid(self)
        if EXT_MAIL: mail.expand_fluid(self)
        if EXT_JWT: jwt.expand_fluid(self)

        if TAILWIND:
            self.startup_hook(lambda: generate_tailwind_css(self))
            jinja_context["wf_tailwind"] = Markup('<link rel="stylesheet" href="/wf-static/css/tailwind.css">')

        if PROCESSING and jinja_context:
            self.context_processor(lambda: jinja_context)

        self.startup_hook(
            lambda: register_additives(self)
        )
        self.startup_hook(self._prepare)
        Frontend.prepare(self)

        self._asgi_app = None
        self._shutdown_flag = asyncio.Event()

        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        weakref.finalize(self, self._finalize)

        super().__init__(**self.config.get("APP_CONFIG", {}))

    def __repr__(self) -> str:
        return f"<WebFluid {version()}>"

    def _prepare(self):
        self.mount(APP_STATIC, self.app_static, "static")
        self.mount(WF_STATIC, self.framework_static, "wf_static")

    async def _startup(self):
        self._startup_lock = True
        for hook in self._hooks["startup"]:
            await safe_execute(hook, EventHookException)

    async def _shutdown(self):
        self._shutdown_lock = True
        for hook in reversed(self._hooks["shutdown"]):
            await safe_execute(hook, EventHookException)

    async def _run_server(self):
        config = uvicorn.Config(
            self.asgi_app,
            host="0.0.0.0",
            port=int(os.getenv("SERVER_PORT", "5000"))
        )
        server = uvicorn.Server(config)
        disable_uvicorn_logging()
        await server.serve()

    def _handle_shutdown(self, signum: int, frame: "FrameType"):
        if self._shutdown_flag.is_set():
            return
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(self._shutdown_flag.set)

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
            raise TypeError("Request processors must receive exactly one argument (request).")
        self._request_processors["before"].append(fn)
        return fn

    def after_request(self, fn: Callable) -> Callable:
        if required_arg_count(fn) != 1:
            raise TypeError("Request processors must receive exactly one argument (response).")
        self._request_processors["after"].append(fn)
        return fn

    async def render(self, template: str, **ctx) -> str:
        for processor in self._context_processors:
            result = await safe_execute(processor, ProcessorException)
            if not isinstance(result, dict): continue
            ctx = result | ctx
        return await self.jinja_env.get_template(template).render_async(**ctx)

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

    @classmethod
    def _finalize(cls):
        for hook in cls._object_hooks["after_deconstruction"]:
            hook()

    @classmethod
    def on_init(cls, fn: Callable) -> Callable:
        cls._object_hooks["before_construction"].append(fn)
        return fn

    @classmethod
    def on_delete(cls, fn: Callable) -> Callable:
        cls._object_hooks["after_deconstruction"].append(fn)
        return fn
