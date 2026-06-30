from webfluid.extensions.cache import legacy, redis, base


class Cache(base.BaseCache):
    def __init__(self, fluid=None):
        self._cache_type = "legacy"
        self._instance = None
        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        self._cache_type = fluid.config.get("CACHE_TYPE", self._cache_type)

        if self._cache_type == "legacy": self._instance = legacy.LegacyCache(fluid)
        elif self._cache_type == "redis": self._instance = redis.RedisCache(fluid)
        else: raise ValueError(f"Unknown cache type: {self._cache_type}")

    def set(self, key, value, timeout=None):
        self._instance.set(key, value, timeout)

    def get(self, key): return self._instance.get(key)
    def delete(self, key): self._instance.delete(key)

    async def aset(self, key, value, timeout=None):
        await self._instance.aset(key, value, timeout)
    async def aget(self, key): return await self._instance.aget(key)
    async def adelete(self, key): await self._instance.adelete(key)

    def clear(self): self._instance.clear()
    async def aclear(self): await self._instance.aclear()
