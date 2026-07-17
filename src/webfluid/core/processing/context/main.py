from datetime import datetime, UTC

from .babel import setup_and_get_locale_fn
from .sources import get_source_callables
from .url_for import url_for
from webfluid.core.constants import FRAMEWORK_ID


def add_processor(fluid):
    get_locale = setup_and_get_locale_fn(fluid)
    theme, sources = get_source_callables(fluid)

    fluid.context_processor(lambda: {
        "LANG": get_locale(),
        "YEAR": datetime.now(UTC).year,

        "id": FRAMEWORK_ID,
        "theme": theme(),
        "src": sources,
        "url_for": url_for()
    })
