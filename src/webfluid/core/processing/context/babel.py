from webfluid.core.constants import EXT_BABEL


def setup_and_get_locale_fn(fluid):
    if EXT_BABEL:
        from webfluid.extensions.babel.utils import get_locale
        return get_locale

    from webfluid.extensions.babel.utils import fake_t, fake_tn
    fluid.jinja_env.add_extension("jinja2.ext.i18n")
    fluid.jinja_env.install_gettext_callables(
        fake_t, fake_tn, newstyle=True
    )

    default_locale = fluid.config["BABEL_DEFAULT_LOCALE"]
    return lambda: default_locale
