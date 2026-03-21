from pathlib import Path

from webfluid.utils.framework import enabled

FRAMEWORK_ROOT = Path(__file__).parent.parent.resolve()

APP_STATIC = "/static"
WF_STATIC = "/wf-static"

DEBUG = enabled("DEBUG_MODE")
TAILWIND = enabled("WF_TAILWIND")
PROCESSING = enabled("WF_PROCESSING")
ADDITIVES = enabled("WF_ADDITIVES")

EXT_SCHEDULING = enabled("EXT_SCHEDULING")
EXT_SQLALCHEMY = enabled("EXT_SQLALCHEMY")
EXT_BABEL = enabled("EXT_BABEL")
EXT_CACHE = enabled("EXT_CACHE")
EXT_MAIL = enabled("EXT_MAIL")
EXT_JWT = enabled("EXT_JWT")
