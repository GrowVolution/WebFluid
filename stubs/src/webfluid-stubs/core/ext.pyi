from apscheduler.schedulers.asyncio import AsyncIOScheduler

from webfluid.extensions import (
    Babel, Cache, EventManager, JWTManager, Mail, Security, SQLAlchemy
)

__all__ = [
    "scheduler", "db", "babel", "security",
    "events", "cache", "mail", "jwt"
]

scheduler: AsyncIOScheduler
db: SQLAlchemy
babel: Babel
security: Security
events: EventManager
cache: Cache
mail: Mail
jwt: JWTManager

def __getattr__(name: str) -> object: ...
