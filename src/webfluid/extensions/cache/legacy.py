from datetime import datetime, timedelta, UTC
from apscheduler.triggers.date import DateTrigger

from webfluid.extensions.cache.base import BaseCache
from webfluid.utils.core import async_result, enabled
from webfluid.exceptions import FrameworkException


class LegacyCache(BaseCache):
    def __init__(self, fluid=None):
        if not enabled("EXT_SCHEDULING"):
            raise FrameworkException("EXT_SCHEDULING is required for LegacyCache to work.")

        super().__init__(fluid)
        self._cache = {}

    def set(self, key, value, timeout=None):
        from webfluid.core.ext import scheduler
        timeout = timeout or self._default_timeout
        self._cache[key] = value
        scheduler.add_job(
            (lambda: self._cache.pop(key)),
            DateTrigger(run_date=datetime.now(UTC) + timedelta(seconds=timeout))
        )

    def get(self, key): return self._cache.get(key)
    def delete(self, key): self._cache.pop(key, None)
    def clear(self): self._cache.clear()

    async def aset(self, key, value, timeout=None):
        await async_result(self.set(key, value, timeout))

    async def aget(self, key): return await async_result(self.get(key))
    async def adelete(self, key): await async_result(self.delete(key))
    async def aclear(self): await async_result(self.clear())
