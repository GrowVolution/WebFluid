from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).parent.parent.resolve()
FRAMEWORK_PACKAGE = __name__.split(".")[0]

FRAMEWORK_ID = "fluid"
FRAMEWORK_NAME = "WebFluid"
FRAMEWORK_ABBR = "wf"
FRAMEWORK_SITE = "https://webfluid.dev/"
FRAMEWORK_DOCS = "https://docs.webfluid.dev/latest/"

HUB_NAME = "Ocean"
HUB_API_URL = "https://ocean.webfluid.dev/hub/api/v1"
HUB_AUTH_URL = "https://ocean.webfluid.dev/auth/api/v1"

CLI_NAME = FRAMEWORK_ABBR
ENV_PREFIX = FRAMEWORK_ABBR.upper()

MAIN_LOGGER = FRAMEWORK_PACKAGE
ADDITIVE_LOGGER = f"{FRAMEWORK_PACKAGE}.additives"
EXTENSION_GROUP = f"{FRAMEWORK_PACKAGE}.extensions"

REQUIRES_KEY = FRAMEWORK_ABBR
IDENTITY_ROUTE = f"/{FRAMEWORK_ABBR}-identity"
HUB_TOKEN_FILE = f".{FRAMEWORK_ABBR}-{HUB_NAME.lower()}"

BASE_TEMPLATE = f"{FRAMEWORK_ID}_base.html"
STATIC_MOUNT = f"{FRAMEWORK_ID}_static"
STATIC_GLOBAL = f"{FRAMEWORK_ABBR}_static"
TAILWIND_GLOBAL = f"{FRAMEWORK_ABBR}_tailwind"
