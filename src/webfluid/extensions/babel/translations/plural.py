from functools import lru_cache


@lru_cache(maxsize=None)
def _plural_rule(locale):
    from webfluid.extensions.babel.utils import load_locale
    return load_locale(locale).plural_form


def plural_form(locale, num):
    return _plural_rule(locale)(num)
