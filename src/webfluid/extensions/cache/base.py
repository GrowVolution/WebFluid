from typing import TYPE_CHECKING, Any, Optional

from webfluid.extensions.base import FluidExtension

if TYPE_CHECKING:
    from webfluid import Fluid


class BaseCache(FluidExtension):
    def __init__(self, fluid: Optional["Fluid"] = None):
        self._default_timeout = 300
        super().__init__(fluid)

    def expand_fluid(self, fluid: "Fluid", *_, **__):
        self._default_timeout = fluid.config.get("CACHE_DEFAULT_TIMEOUT", self._default_timeout)

    def set(self, key: str, value: Any, timeout: int = None): raise NotImplementedError()
    def get(self, key: str): raise NotImplementedError()
    def delete(self, key: str): raise NotImplementedError()

    async def aset(self, key: str, value: Any, timeout: int = None): raise NotImplementedError()
    async def aget(self, key: str): raise NotImplementedError()
    async def adelete(self, key: str): raise NotImplementedError()

    def clear(self): raise NotImplementedError()
    async def aclear(self): raise NotImplementedError()
