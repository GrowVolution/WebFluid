from importlib import import_module
from typing import TYPE_CHECKING, Callable
import os

from webfluid.additives.core import installed_additives
from webfluid.utils.framework import enabled, check_priority, build_sorted_tuple, try_import

if TYPE_CHECKING:
    from webfluid.core.fluid import Fluid

_config_map: dict[int, list[type]] = {}

class _ConfigMeta(type): pass


class Config(dict):
    def from_object(self, obj: object | str):
        if isinstance(obj, str):
            obj = import_module(obj)
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)


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
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = "lax"

    PROXY_FIX = False

    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = f"{os.getenv('REDIS_URI', 'redis://localhost:6379')}/1"
    RATELIMIT_DEFAULT = ["500/day", "100/hour"]

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///app.db")

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


def init_configs(fluid: "Fluid"):
    try_import("fluid.config")

    additives = fluid.app_root / "additives"
    if not additives.exists() or not additives.is_dir(): return
    for additive in installed_additives(additives, cache=False):
        a, _, p = additive
        if not enabled(a): continue
        try_import(f"additives.{p}.config")


def register_config(priority: int = 1) -> Callable:
    check_priority(priority)

    def decorator(cls):
        if not priority in _config_map:
            _config_map[priority] = []

        if not isinstance(type(cls), _ConfigMeta):
            cls = _ConfigMeta(cls.__name__, cls.__bases__, dict(cls.__dict__))

        _config_map[priority].append(cls)
        return cls

    return decorator


def build_config() -> _ConfigMeta:
    cls = DefaultConfig
    default_conf = _ConfigMeta(cls.__name__, cls.__bases__, dict(cls.__dict__))

    bases = tuple()
    for configs in build_sorted_tuple(_config_map):
        bases += tuple(configs)

    return _ConfigMeta(
        "Config",
        bases + (default_conf,),
        {}
    )
