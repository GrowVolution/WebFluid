import os

from webfluid.utils import enabled


class DefaultConfig:
    SERVER_NAME = os.getenv("SERVER_NAME")
    SECRET_KEY = os.getenv("SECRET_KEY", "151ca2beba81560d3fd5d16a38275236")

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    MAX_FORM_MEMORY_SIZE = 16 * 1024 * 1024

    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = f"{os.getenv('REDIS_URL', 'redis://localhost:6379')}/1"
    RATELIMIT_DEFAULT = "500 per day; 100 per hour"
    RATELIMIT_STRATEGY = "fixed-window"

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECURITY_PASSWORD_SALT = os.getenv("SECURITY_PASSWORD_SALT", "8869a5e751c061792cd0be92b5631f25")
    SECURITY_REGISTERABLE = True
    SECURITY_SEND_REGISTER_EMAIL = False
    SECURITY_UNAUTHORIZED_VIEW = None
    SECURITY_TWO_FACTOR = False

    OAUTH_CLIENTS = {}

    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 25))
    MAIL_USE_TLS = enabled("MAIL_USE_TLS")
    MAIL_USE_STARTTLS = enabled("MAIL_USE_STARTTLS")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@example.com")

    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_URL = f"{os.getenv('REDIS_URL', 'redis://localhost:6379')}/2"
    CACHE_DEFAULT_TIMEOUT = 300
