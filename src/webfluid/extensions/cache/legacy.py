from heapq import heappush, heappop
from time import monotonic

from webfluid.extensions.cache.base import BaseCache


class LegacyCache(BaseCache):
    def __init__(self, fluid=None):
        self._cache = {}
        self._expiry = []
        super().__init__(fluid)

    def _sweep(self):
        now = monotonic()
        while self._expiry and self._expiry[0][0] <= now:
            expires, key = heappop(self._expiry)
            entry = self._cache.get(key)
            if entry is not None and entry[0] == expires:
                del self._cache[key]

    def set(self, key, value, timeout=None):
        self._sweep()
        expires = monotonic() + (timeout or self._default_timeout)
        self._cache[key] = (expires, value)
        heappush(self._expiry, (expires, key))

    def get(self, key):
        entry = self._cache.get(key)
        if entry is None: return None

        if entry[0] <= monotonic():
            self._cache.pop(key, None)
            return None

        return entry[1]

    def delete(self, key): self._cache.pop(key, None)

    def clear(self):
        self._cache.clear()
        self._expiry.clear()

    async def aset(self, key, value, timeout=None): self.set(key, value, timeout)
    async def aget(self, key): return self.get(key)
    async def adelete(self, key): self.delete(key)
    async def aclear(self): self.clear()
