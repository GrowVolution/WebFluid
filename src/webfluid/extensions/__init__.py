
__all__ = [
    "FluidExtension",

    "SQLAlchemy", "Babel", "Security", "OAuth",
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

    if name == "Security":
        from .security.security import Security
        return Security

    if name == "OAuth":
        from .security.oauth import OAuth
        return OAuth

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
