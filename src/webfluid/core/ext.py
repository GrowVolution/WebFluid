from apscheduler.schedulers.asyncio import AsyncIOScheduler

from webfluid.extensions import SQLAlchemy, Babel, EventManager, Mail, Cache, JWTManager


scheduler = AsyncIOScheduler()

db = SQLAlchemy()
babel = Babel()
events = EventManager()
cache = Cache()
mail = Mail()
jwt = JWTManager()
