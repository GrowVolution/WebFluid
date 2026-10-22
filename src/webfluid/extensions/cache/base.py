from abc import abstractmethod

from webfluid.extensions.base import FluidExtension


class BaseCache(FluidExtension):
    def __init__(self, fluid=None):
        self._default_timeout = 300
        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        self._default_timeout = fluid.config["CACHE_DEFAULT_TIMEOUT"]

    def _ttl(self, timeout):
        ttl = self._default_timeout if timeout is None else timeout
        return ttl or None

    @abstractmethod
    def set(self, key, value, timeout=None): ...
    @abstractmethod
    def get(self, key): ...
    @abstractmethod
    def delete(self, key): ...
    @abstractmethod
    def clear(self): ...

    @abstractmethod
    async def aset(self, key, value, timeout=None): ...
    @abstractmethod
    async def aget(self, key): ...
    @abstractmethod
    async def adelete(self, key): ...
    @abstractmethod
    async def aclear(self): ...
