from apscheduler.schedulers.asyncio import AsyncIOScheduler

from webfluid.extensions import (
    SQLAlchemy, Babel, Security, EventManager, Mail, Cache, JWTManager
)


scheduler = AsyncIOScheduler()

db = SQLAlchemy()
babel = Babel()
security = Security()
events = EventManager()
cache = Cache()
mail = Mail()
jwt = JWTManager()
