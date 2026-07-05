
__all__ = ["BaseCache", "Cache"]


def __getattr__(name):
    if name == "BaseCache":
        from .base import BaseCache
        return BaseCache

    if name == "Cache":
        from .cache import Cache
        return Cache

    raise AttributeError(name)
