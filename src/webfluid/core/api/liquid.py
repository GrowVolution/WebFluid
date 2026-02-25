from fastapi import FastAPI, Request, Response
from aioflask import Config
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from werkzeug.http import parse_accept_header
from werkzeug.datastructures import LanguageAccept
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from typing import Callable, TYPE_CHECKING

from webfluid.core.context import FluidContext
from webfluid.core.ext import babel
from webfluid.utils.config import build_api_config

if TYPE_CHECKING:
    from webfluid import Fluid


class ApiLiquid(FastAPI):
    def __init__(self, fluid: "Fluid"):
        self.config = Config(fluid.app_root)
        self.config.from_object(build_api_config())

        super().__init__(**self.config.get("API_CONFIG", {}))

        if self.config.get("RATELIMIT_ENABLED", True):
            self.state.limiter = Limiter(
                key_func=get_remote_address,
                default_limits=self.config.get(
                    "RATELIMIT_DEFAULT", ["500/day", "100/hour"]
                ),
                storage_uri=self.config.get("RATELIMIT_STORAGE_URI", "redis://localhost:6379/1"),
            )
            self.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        async def _context_middleware(
            request: Request, call_next: Callable
        ) -> Response:
            async with FluidContext(fluid, request):
                return await call_next(request)

        self.middleware("http")(_context_middleware)

        self._asgi = None

    @property
    def asgi(self) -> "ApiLiquid | ProxyHeadersMiddleware":
        if self._asgi is not None: return self._asgi

        if self.config.get("PROXY_FIX", False):
            self._asgi = ProxyHeadersMiddleware(self)
        else:
            self._asgi = self

        return self._asgi

    @property
    def limit(self) -> Callable:
        if self.config.get("RATELIMIT_ENABLED", True):
            return self.state.limiter.limit
        return lambda *_, **__: lambda fn: fn
