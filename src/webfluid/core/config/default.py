import os


class DefaultConfig:
    APP_CONFIG = {
        "title": "WebFluid Application",
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

    PROXY_FIX = False
    PROXY_TRUSTED_HOSTS = "127.0.0.1"

    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = f"{os.getenv('REDIS_URI', 'redis://localhost:6379')}/1"
    RATELIMIT_DEFAULT = ["500/day", "100/hour"]

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///app.db")
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 3600
    }

    BABEL_DISABLE_AUTOUPDATE = False

    SECURITY_SECRET = os.getenv("SECURITY_SECRET")
    SECURITY_TOKEN_MAX_AGE = 3600
    SECURITY_CSRF_COOKIE_NAME = "csrf_token"
    SECURITY_CSRF_COOKIE_SECURE = True
    SECURITY_HASHER_TIME_COST = 3
    SECURITY_HASHER_MEMORY_COST = 65536
    SECURITY_HASHER_PARALLELISM = 4
    SECURITY_PASSWORD_MIN_LENGTH = 8
    SECURITY_PASSWORD_REQUIREMENTS = {
        "lower": 1,
        "upper": 1,
        "digits": 1,
        "special": 1
    }

    MAIL_SERVER = "localhost"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_STARTTLS = False
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = MAIL_USERNAME if MAIL_USERNAME else "noreply@example.com"

    CACHE_TYPE = "redis"
    CACHE_REDIS_URI = f"{os.getenv('REDIS_URI', 'redis://localhost:6379')}/2"
    CACHE_DEFAULT_TIMEOUT = 300
