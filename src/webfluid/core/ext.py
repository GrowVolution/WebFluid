from apscheduler.schedulers.asyncio import AsyncIOScheduler

from webfluid.extensions import (
    SQLAlchemy, Babel, Security, EventManager, Mail, Cache, JWTManager
)


scheduler = AsyncIOScheduler()

db: SQLAlchemy = SQLAlchemy()
babel: Babel = Babel()
security: Security = Security()
events: EventManager = EventManager()
cache: Cache = Cache()
mail: Mail = Mail()
jwt: JWTManager = JWTManager()
