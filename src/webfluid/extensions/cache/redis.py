from redis import Redis as SyncRedis
from redis.asyncio import Redis as AsyncRedis
from typing import TYPE_CHECKING

from webfluid.extensions.cache.base import BaseCache

if TYPE_CHECKING:
    from webfluid import Fluid


class RedisCache(BaseCache):
    def __init__(self, fluid: "Fluid | None" = None):
        self._redis_uri = "redis://localhost:6379"
        self._cache = None
        self._acache = None

        super().__init__(fluid)

    def init_fluid(self, fluid: "Fluid"):
        self._redis_uri = fluid.app.config.get("CACHE_REDIS_URI", self._redis_uri)
        self._cache = SyncRedis.from_url(self._redis_uri, decode_responses=True)
        self._acache = AsyncRedis.from_url(self._redis_uri, decode_responses=True)
        super().init_fluid(fluid)

    def set(self, key: str, value: str, timeout: int = None):
        timeout = timeout or self._default_timeout
        self._cache.set(key, value, ex=timeout)

    def get(self, key: str): return self._cache.get(key)
    def delete(self, key: str): self._cache.delete(key)

    async def aset(self, key: str, value: str, timeout: int = None):
        timeout = timeout or self._default_timeout
        await self._acache.set(key, value, ex=timeout)

    async def aget(self, key: str): return await self._acache.get(key)
    async def adelete(self, key: str): await self._acache.delete(key)

    def clear(self): self._cache.flushdb()
    async def aclear(self): await self._acache.flushdb()
