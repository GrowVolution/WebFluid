from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis

from webfluid.extensions.cache.base import BaseCache


class RedisCache(BaseCache):
    def __init__(self, fluid=None):
        self._redis_uri = "redis://localhost:6379"
        self._cache = None
        self._acache = None

        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        self._redis_uri = fluid.config.get("CACHE_REDIS_URI", self._redis_uri)
        self._cache = SyncRedis.from_url(self._redis_uri, decode_responses=True)
        self._acache = AsyncRedis.from_url(self._redis_uri, decode_responses=True)
        super().expand_fluid(fluid)

    def set(self, key, value, timeout=None):
        timeout = timeout or self._default_timeout
        self._cache.set(key, value, ex=timeout)

    def get(self, key): return self._cache.get(key)
    def delete(self, key): self._cache.delete(key)
    def clear(self): self._cache.flushdb()

    async def aset(self, key, value, timeout=None):
        timeout = timeout or self._default_timeout
        await self._acache.set(key, value, ex=timeout)

    async def aget(self, key): return await self._acache.get(key)
    async def adelete(self, key): await self._acache.delete(key)
    async def aclear(self): await self._acache.flushdb()
