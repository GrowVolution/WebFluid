from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid.extensions.base import FluidExtension
    from webfluid.extensions.sqlalchemy import SQLAlchemy
    from webfluid.extensions.babel.babel import Babel
    from webfluid.extensions.events import EventManager
    from webfluid.extensions.mailman import Mail
    from webfluid.extensions.cache.cache import Cache
    from webfluid.extensions.jwt import JWTManager

__all__ = [
    "FluidExtension",

    "SQLAlchemy", "Babel", "EventManager",
    "Mail", "Cache", "JWTManager",

    "babel", "cache", "utils"
]


def __getattr__(name):
    if name == "FluidExtension":
        from .base import FluidExtension
        return FluidExtension

    if name == "SQLAlchemy":
        from .sqlalchemy import SQLAlchemy
        return SQLAlchemy

    if name == "Babel":
        from .babel.babel import Babel
        return Babel

    if name == "EventManager":
        from .events import EventManager
        return EventManager

    if name == "Mail":
        from .mailman import Mail
        return Mail

    if name == "Cache":
        from .cache.cache import Cache
        return Cache

    if name == "JWTManager":
        from .jwt import JWTManager
        return JWTManager

    raise AttributeError(name)
