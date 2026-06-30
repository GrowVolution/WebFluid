from collections.abc import Callable
from typing import Any

from webfluid.core.fluid import Fluid

_config_map: dict[int, list[type]]

class _ConfigMeta(type): ...

class Config(dict[str, Any]):
    def from_object(self, obj: object | str) -> None: ...

class DefaultConfig:
    APP_CONFIG: dict[str, Any]
    APP_FRONTEND: dict[str, Any]
    BASE_URL: str
    SECRET_KEY: str | None

    SESSION_COOKIE_NAME: str
    SESSION_COOKIE_SAMESITE: str

    PROXY_FIX: bool

    RATELIMIT_ENABLED: bool
    RATELIMIT_STORAGE_URI: str
    RATELIMIT_DEFAULT: list[str]

    SQLALCHEMY_DATABASE_URI: str

    BABEL_DISABLE_AUTOUPDATE: bool

    SECURITY_SECRET: str | None
    SECURITY_TOKEN_MAX_AGE: int
    SECURITY_CSRF_COOKIE_NAME: str
    SECURITY_CSRF_COOKIE_SECURE: bool
    SECURITY_HASHER_TIME_COST: int
    SECURITY_HASHER_MEMORY_COST: int
    SECURITY_HASHER_PARALLELISM: int
    SECURITY_PASSWORD_MIN_LENGTH: int
    SECURITY_PASSWORD_REQUIREMENTS: dict[str, int]

    MAIL_SERVER: str
    MAIL_PORT: int
    MAIL_USE_TLS: bool
    MAIL_USE_STARTTLS: bool
    MAIL_USERNAME: str | None
    MAIL_PASSWORD: str | None
    MAIL_DEFAULT_SENDER: str

    CACHE_TYPE: str
    CACHE_REDIS_URI: str
    CACHE_DEFAULT_TIMEOUT: int

def init_configs(fluid: Fluid) -> None: ...
def register_config(priority: int = 1) -> Callable[[type], type]: ...
def build_config() -> _ConfigMeta: ...
