from datetime import datetime, timedelta, UTC
from apscheduler.triggers.date import DateTrigger
from typing import TYPE_CHECKING, Any

from webfluid.extensions.cache.base import BaseCache
from webfluid.utils import async_result, enabled
from webfluid.exceptions import FrameworkException

if TYPE_CHECKING:
    from webfluid import Fluid


class LegacyCache(BaseCache):
    def __init__(self, fluid: "Fluid | None" = None):
        if not enabled("EXT_SCHEDULING"):
            raise FrameworkException("EXT_SCHEDULING is required for LegacyCache to work.")

        super().__init__(fluid)
        self._cache = {}

    def set(self, key: str, value: Any, timeout: int = None):
        from webfluid.core.ext import scheduler
        timeout = timeout or self._default_timeout
        self._cache[key] = value
        scheduler.add_job(
            (lambda: self._cache.pop(key)),
            DateTrigger(run_date=datetime.now(UTC) + timedelta(seconds=timeout))
        )

    def get(self, key: str) -> Any | None: return self._cache.get(key)
    def delete(self, key: str): self._cache.pop(key, None)

    async def aset(self, key: str, value: Any, timeout: int = None):
        await async_result(self.set(key, value, timeout))

    async def aget(self, key: str) -> Any | None: return await async_result(self.get(key))
    async def adelete(self, key: str): return await async_result(self.delete(key))

    def clear(self): self._cache.clear()
    async def aclear(self): await async_result(self.clear())
