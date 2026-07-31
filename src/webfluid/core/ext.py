
__all__ = [
    "scheduler", "db", "babel", "security",
    "events", "cache", "mail", "jwt"
]


def __getattr__(name):
    if name == "scheduler":
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        instance = AsyncIOScheduler()

    elif name == "db":
        from webfluid.extensions import SQLAlchemy
        instance = SQLAlchemy()

    elif name == "babel":
        from webfluid.extensions import Babel
        instance = Babel()

    elif name == "security":
        from webfluid.extensions import Security
        instance = Security()

    elif name == "events":
        from webfluid.extensions import EventManager
        instance = EventManager()

    elif name == "cache":
        from webfluid.extensions import Cache
        instance = Cache()

    elif name == "mail":
        from webfluid.extensions import Mail
        instance = Mail()

    elif name == "jwt":
        from webfluid.extensions import JWTManager
        instance = JWTManager()

    else: raise AttributeError(name)

    globals()[name] = instance
    return instance
