from pathlib import Path
import os

from webfluid.utils.core import enabled

FRAMEWORK_ROOT = Path(__file__).parent.parent.resolve()
FRAMEWORK_ID = "fluid"

APP_STATIC = "/static"
WF_STATIC = f"/{FRAMEWORK_ID}/static"
WF_OCEAN = os.getenv("OCEAN_API", "https://ocean.webfluid.dev/hub/api/v1")
OCEAN_AUTH = os.getenv("AUTH_API", "https://ocean.webfluid.dev/auth/api/v1")

DEBUG = enabled("DEBUG_MODE")
EXECUTION = enabled("IN_EXECUTION")
THEMES = enabled("WF_THEMES")
TAILWIND = enabled("WF_TAILWIND")
PROCESSING = enabled("WF_PROCESSING")
ADDITIVES = enabled("WF_ADDITIVES")

EXT_SCHEDULING = enabled("EXT_SCHEDULING")
EXT_SQLALCHEMY = enabled("EXT_SQLALCHEMY")
EXT_BABEL = enabled("EXT_BABEL")
EXT_SECURITY = enabled("EXT_SECURITY")
EXT_EVENTS = enabled("EXT_EVENTS")
EXT_CACHE = enabled("EXT_CACHE")
EXT_MAIL = enabled("EXT_MAIL")
EXT_JWT = enabled("EXT_JWT")

DEV_AUTO_INSTALL = enabled("DEV_AUTO_INSTALL")
