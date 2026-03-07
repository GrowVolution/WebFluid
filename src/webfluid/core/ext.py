from authlib.integrations.starlette_client import OAuth
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from webfluid.extensions import Socket, SQLAlchemy, Babel, Mail, Cache, JWTManager

socket = Socket(async_mode="asgi")
scheduler = AsyncIOScheduler()

db = SQLAlchemy()
babel = Babel()
oauth = OAuth()
cache = Cache()
mail = Mail()
jwt = JWTManager()
