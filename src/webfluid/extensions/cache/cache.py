from importlib import import_module

from webfluid.extensions.base import FluidExtension
from webfluid.exceptions import FrameworkException

_backends = {
    "legacy": ("webfluid.extensions.cache.legacy", "LegacyCache"),
    "redis": ("webfluid.extensions.cache.redis", "RedisCache")
}


class Cache(FluidExtension):
    def __init__(self, fluid=None):
        self._cache_type = "legacy"
        self._instance = None
        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        self._cache_type = fluid.config["CACHE_TYPE"].lower()

        backend = _backends.get(self._cache_type)
        if backend is None:
            raise ValueError(f"Unknown cache type: {self._cache_type}")

        module, attribute = backend
        self._instance = getattr(import_module(module), attribute)(fluid)

    @property
    def backend(self):
        if self._instance is None:
            raise FrameworkException("Cache.expand_fluid() has not been called.")
        return self._instance

    def set(self, key, value, timeout=None):
        self.backend.set(key, value, timeout)

    def get(self, key): return self.backend.get(key)
    def delete(self, key): self.backend.delete(key)
    def clear(self): self.backend.clear()

    async def aset(self, key, value, timeout=None):
        await self.backend.aset(key, value, timeout)

    async def aget(self, key): return await self.backend.aget(key)
    async def adelete(self, key): await self.backend.adelete(key)
    async def aclear(self): await self.backend.aclear()
