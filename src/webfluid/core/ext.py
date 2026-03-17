from apscheduler.schedulers.asyncio import AsyncIOScheduler

from webfluid.extensions import SQLAlchemy, Babel, Mail, Cache, JWTManager


scheduler = AsyncIOScheduler()

db = SQLAlchemy()
babel = Babel()
cache = Cache()
mail = Mail()
jwt = JWTManager()
