from webfluid.extensions.base import FluidExtension


class BaseCache(FluidExtension):
    def __init__(self, fluid=None):
        self._default_timeout = 300
        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        self._default_timeout = fluid.config["CACHE_DEFAULT_TIMEOUT"]

    def set(self, key, value, timeout=None): raise NotImplementedError()
    def get(self, key): raise NotImplementedError()
    def delete(self, key): raise NotImplementedError()
    def clear(self): raise NotImplementedError()

    async def aset(self, key, value, timeout=None): raise NotImplementedError()
    async def aget(self, key): raise NotImplementedError()
    async def adelete(self, key): raise NotImplementedError()
    async def aclear(self): raise NotImplementedError()
