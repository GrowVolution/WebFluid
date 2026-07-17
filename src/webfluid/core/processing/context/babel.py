from webfluid.core.constants import EXT_BABEL
from webfluid.extensions.babel.utils import (
    get_locale as _get_locale, fake_t, fake_tn
)


def setup_and_get_locale_fn(fluid):
    if not EXT_BABEL:
        fluid.jinja_env.add_extension("jinja2.ext.i18n")
        fluid.jinja_env.install_gettext_callables(
            fake_t, fake_tn, newstyle=True
        )
        default_locale = fluid.config.get("BABEL_DEFAULT_LOCALE", "en")
        get_locale = lambda: default_locale
    else:
        get_locale = _get_locale

    return get_locale
