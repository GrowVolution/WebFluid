from fastapi import APIRouter
from functools import wraps

from webfluid.utils.core import async_result
from webfluid.utils.logging import factory as log_factory


class Router(APIRouter):
    def __init__(self, *args, **kwargs):
        self._http_middleware = []
        super().__init__(*args, **kwargs)

    def http_middleware(self, fn):
        self._http_middleware.append(fn)
        return fn

    def _wrapped(self, endpoint):
        chain = None

        @wraps(endpoint)
        async def wrapper(*args, **kwargs):
            nonlocal chain
            if chain is None:
                chain = endpoint
                for middleware in reversed(self._http_middleware):
                    chain = middleware(chain)
            return await async_result(chain(*args, **kwargs))

        return log_factory.additive_context(wrapper)

    def add_api_route(self, path, endpoint, **kwargs):
        super().add_api_route(path, self._wrapped(endpoint), **kwargs)

    def add_api_websocket_route(self, path, endpoint, name=None, **kwargs):
        super().add_api_websocket_route(
            path, log_factory.additive_context(endpoint), name=name, **kwargs
        )
