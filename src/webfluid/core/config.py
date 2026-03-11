from importlib import import_module
import os

from webfluid.utils import enabled


class Config(dict):
    def from_object(self, obj: object | str):
        if isinstance(obj, str):
            obj = import_module(obj)
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)


class DefaultConfig:
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
    API_CONFIG = {
        "title": "WebFluid API",
        "version": "1.0.0",
        "root_path": "/api/v1",
    }
    SECRET_KEY = os.getenv("SECRET_KEY", "151ca2beba81560d3fd5d16a38275236")

    PROXY_FIX = False

    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = f"{os.getenv('REDIS_URL', 'redis://localhost:6379')}/1"
    RATELIMIT_DEFAULT = ["500/day", "100/hour"]

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///app.db")

    OAUTH_CLIENTS = {}

    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 25))
    MAIL_USE_TLS = enabled("MAIL_USE_TLS")
    MAIL_USE_STARTTLS = enabled("MAIL_USE_STARTTLS")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@example.com")

    CACHE_TYPE = "redis"
    CACHE_REDIS_URI = f"{os.getenv('REDIS_URI', 'redis://localhost:6379')}/2"
    CACHE_DEFAULT_TIMEOUT = 300
