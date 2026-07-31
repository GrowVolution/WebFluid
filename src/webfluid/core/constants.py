import os

from webfluid.core.identity import (
    FRAMEWORK_ID, ENV_PREFIX,
    HUB_NAME, HUB_API_URL, HUB_AUTH_URL
)
from webfluid.utils.core import enabled

APP_STATIC = "/static"
FRAMEWORK_STATIC = f"/{FRAMEWORK_ID}/static"

HUB_API = os.getenv(f"{HUB_NAME.upper()}_API", HUB_API_URL)
HUB_AUTH = os.getenv(f"{HUB_NAME.upper()}_AUTH", HUB_AUTH_URL)

FEATURE_FLAGS = tuple(f"{ENV_PREFIX}_{name}" for name in (
    "THEMES", "TAILWIND", "CHECK_FRONTEND",
    "BUILD_FRONTEND", "PROCESSING", "ADDITIVES"
))
EXTENSION_FLAGS = tuple(f"EXT_{name}" for name in (
    "SCHEDULING", "SQLALCHEMY", "BABEL", "SECURITY",
    "EVENTS", "CACHE", "MAIL", "JWT"
))

DEBUG = enabled("DEBUG_MODE")
EXECUTION = enabled("IN_EXECUTION")

(
    THEMES, TAILWIND, CHECK_FRONTEND,
    BUILD_FRONTEND, PROCESSING, ADDITIVES
) = map(enabled, FEATURE_FLAGS)

(
    EXT_SCHEDULING, EXT_SQLALCHEMY, EXT_BABEL, EXT_SECURITY,
    EXT_EVENTS, EXT_CACHE, EXT_MAIL, EXT_JWT
) = map(enabled, EXTENSION_FLAGS)

DEV_AUTO_INSTALL = enabled("DEV_AUTO_INSTALL")
