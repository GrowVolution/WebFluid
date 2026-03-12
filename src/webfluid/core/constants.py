from pathlib import Path

from webfluid.utils import enabled

FRAMEWORK_ROOT = Path(__file__).parent.parent.resolve()
DEBUG = enabled("DEBUG_MODE")
TAILWIND = enabled("WF_TAILWIND")
