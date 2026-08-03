from datetime import datetime, UTC

from .babel import setup_and_get_locale_fn
from .sources import get_source_callables
from .url_for import url_for
from webfluid.core.identity import FRAMEWORK_ID


def install_context(fluid):
    get_locale = setup_and_get_locale_fn(fluid)
    theme, sources = get_source_callables(fluid)

    @fluid.context_processor
    def framework_context():
        return {
            "LANG": get_locale(),
            "YEAR": datetime.now(UTC).year,

            "id": FRAMEWORK_ID,
            "theme": theme(),
            "src": sources,
            "url_for": url_for(fluid)
        }
