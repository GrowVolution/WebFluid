from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid.extensions.cache.base import BaseCache
    from webfluid.extensions.cache.cache import Cache

__all__ = ["BaseCache", "Cache"]


def __getattr__(name):
    if name == "BaseCache":
        from .base import BaseCache
        return BaseCache

    if name == "Cache":
        from .cache import Cache
        return Cache

    raise AttributeError(name)
