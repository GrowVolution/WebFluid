from webfluid.extensions.cache.base import BaseCache


class RedisCache(BaseCache):
    def __init__(self, fluid=None):
        self._redis_uri = "redis://localhost:6379"
        self._sync = None
        self._async = None

        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        self._redis_uri = fluid.config["CACHE_REDIS_URI"]
        super().expand_fluid(fluid)

    @property
    def cache(self):
        if self._sync is None:
            from redis import Redis
            self._sync = Redis.from_url(self._redis_uri, decode_responses=True)
        return self._sync

    @property
    def acache(self):
        if self._async is None:
            from redis.asyncio import Redis
            self._async = Redis.from_url(self._redis_uri, decode_responses=True)
        return self._async

    def set(self, key, value, timeout=None):
        self.cache.set(key, value, ex=timeout or self._default_timeout)

    def get(self, key): return self.cache.get(key)
    def delete(self, key): self.cache.delete(key)
    def clear(self): self.cache.flushdb()

    async def aset(self, key, value, timeout=None):
        await self.acache.set(key, value, ex=timeout or self._default_timeout)

    async def aget(self, key): return await self.acache.get(key)
    async def adelete(self, key): await self.acache.delete(key)
    async def aclear(self): await self.acache.flushdb()
