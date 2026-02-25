from flask_migrate import Migrate
from flask_security import Security
from authlib.integrations.flask_client import OAuth
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from webfluid.extensions import Socket, SQLAlchemy, Babel, Mail, Cache, JWTManager

socket = Socket(async_mode="asgi")
scheduler = AsyncIOScheduler()

db = SQLAlchemy()
migrate = Migrate()
babel = Babel()
security = Security()
oauth = OAuth()
cache = Cache()
mail = Mail()
jwt = JWTManager()
