
__all__ = [
    "FluidExtension",

    "SQLAlchemy", "Babel", "Security", "EventManager",
    "Mail", "Cache", "JWTManager",

    "babel", "cache", "sqlalchemy", "security"
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

    if name == "Security":
        from .security.security import Security
        return Security

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

    if name in {"babel", "cache", "sqlalchemy", "security"}:
        from importlib import import_module
        return import_module(f".{name}", __name__)

    raise AttributeError(name)


def __dir__(): return sorted(__all__)
