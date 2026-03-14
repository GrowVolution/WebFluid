from importlib import import_module
from typing import TYPE_CHECKING, Callable
import os

from webfluid.additives import installed_additives
from webfluid.utils import enabled, check_priority, build_sorted_tuple

if TYPE_CHECKING:
    from webfluid import Fluid

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
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
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


def init_configs(fluid: "Fluid"):
    try: import_module("fluid.config")
    except ModuleNotFoundError: pass

    additives = fluid.app_root / "additives"
    if not additives.exists() or not additives.is_dir(): return
    for additive in installed_additives(additives, True):
        a, _, p = additive
        if not enabled(a): continue
        try: import_module(f"additives.{p}.config")
        except ModuleNotFoundError: pass


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
