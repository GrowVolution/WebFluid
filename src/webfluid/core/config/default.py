import os

from webfluid.core.constants import DEBUG
from webfluid.core.identity import FRAMEWORK_ID, FRAMEWORK_NAME
from webfluid.extensions.babel.constants import (
    DEFAULT_DATE_FORMATS, DEFAULT_LOCALE, DEFAULT_TIMEZONE
)

_redis = os.getenv("REDIS_URI", "redis://localhost:6379")


class DefaultConfig:
    APP_CONFIG = {
        "title": f"{FRAMEWORK_NAME} Application",
        "version": "1.0.0"
    }
    APP_FRONTEND = {
        "type": "htmx",
        "alpine": True
    }
    BASE_URL = f"http://localhost:8000"
    SECRET_KEY = os.getenv("SECRET_KEY")

    SESSION_COOKIE_NAME = "session"
    SESSION_COOKIE_SAMESITE = "lax"
    SESSION_COOKIE_SECURE = not DEBUG

    GLOBAL_THEME = FRAMEWORK_ID

    PROXY_FIX = False
    PROXY_TRUSTED_HOSTS = "127.0.0.1"

    STATIC_MAX_AGE = 0 if DEBUG else 31536000

    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = f"{_redis}/1"
    RATELIMIT_DEFAULT = ["500/day", "100/hour"]

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///app.db")
    SQLALCHEMY_BINDS = {}
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 3600
    }

    BABEL_DISABLE_AUTOUPDATE = False
    BABEL_DEFAULT_LOCALE = DEFAULT_LOCALE
    BABEL_DEFAULT_TIMEZONE = DEFAULT_TIMEZONE
    BABEL_SUPPORTED_LOCALES = [DEFAULT_LOCALE]
    BABEL_DATE_FORMATS = DEFAULT_DATE_FORMATS
    BABEL_CONFIGURE_JINJA = True
    BABEL_CONFIGURE_SOCKET = True
    BABEL_DATABASE_BIND = None

    EVENTS_EVENT_QUEUE_SIZE = 5
    EVENTS_CONFIGURE_SOCKET = True

    SECURITY_SECRET = os.getenv("SECURITY_SECRET")
    SECURITY_TOKEN_MAX_AGE = 3600
    SECURITY_CSRF_COOKIE_NAME = "csrf_token"
    SECURITY_CSRF_COOKIE_SECURE = True
    SECURITY_HASHER_TIME_COST = 3
    SECURITY_HASHER_MEMORY_COST = 65536
    SECURITY_HASHER_PARALLELISM = 4
    SECURITY_HASHER_THREADS = 4
    SECURITY_PASSWORD_MIN_LENGTH = 8
    SECURITY_PASSWORD_REQUIREMENTS = {
        "lower": 1,
        "upper": 1,
        "digits": 1,
        "special": 1
    }
    SECURITY_OAUTH_CLIENTS = {}
    SECURITY_MODELS_DB_BIND = None

    JWT_ROTARY_INTERVAL = 15
    JWT_SECRET_LENGTH = 128
    JWT_EXPIRY_DAYS = 30
    JWT_ALGORITHM = "HS256"
    JWT_ISSUER = FRAMEWORK_NAME
    JWT_AUDIENCES = {
        "default": "Application"
    }

    MAIL_SERVER = "localhost"
    MAIL_PORT = 587
    MAIL_USE_TLS = False
    MAIL_USE_STARTTLS = True
    MAIL_TIMEOUT = 10
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = MAIL_USERNAME if MAIL_USERNAME else "noreply@example.com"

    CACHE_TYPE = "redis"
    CACHE_REDIS_URI = f"{_redis}/2"
    CACHE_DEFAULT_TIMEOUT = 300
