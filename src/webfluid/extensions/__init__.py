
__all__ = [
    "FluidExtension",

    "SQLAlchemy", "Babel", "Security", "EventBus",
    "Mail", "Cache", "JWTManager",

    "babel", "cache", "sqlalchemy", "security"
]


def __getattr__(name):
    if name == "FluidExtension":
        from .base import FluidExtension
        return FluidExtension

    if name == "SQLAlchemy":
        from .sqlalchemy.main import SQLAlchemy
        return SQLAlchemy

    if name == "Babel":
        from .babel.main import Babel
        return Babel

    if name == "Security":
        from .security.main import Security
        return Security

    if name == "EventBus":
        from .events.main import EventBus
        return EventBus

    # TODO(1.1): drop the pre-rc1 alias EventManager once 1.1 may break public names.
    if name == "EventManager":
        from .events.main import EventBus
        return EventBus

    if name == "Mail":
        from .mailman.main import Mail
        return Mail

    if name == "Cache":
        from .cache.main import Cache
        return Cache

    if name == "JWTManager":
        from .jwt.main import JWTManager
        return JWTManager

    if name in {"babel", "cache", "sqlalchemy", "security"}:
        from importlib import import_module
        return import_module(f".{name}", __name__)

    raise AttributeError(name)


def __dir__(): return sorted(__all__)
