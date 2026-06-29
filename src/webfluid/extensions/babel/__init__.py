from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid.extensions.babel.babel import Babel
    from webfluid.extensions.babel.domain import Domain
    from webfluid.extensions.babel.translations import (
        MergedTranslations as Translations, I18nMessage
    )
    from webfluid.extensions.babel.speaklater import LazyString
    from webfluid.extensions.babel.utils import *

__all__ = [
    "Babel", "Domain",
    "Translations", "I18nMessage",
    "LazyString",

    "translation_resolver", "parse_best_match", "load_locale", "get_locale",
    "get_timezone", "format_message", "format_datetime", "format_date", "format_time",
    "format_timedelta", "format_number", "format_decimal", "format_percent", "format_currency",
    "format_scientific", "to_user_timezone", "to_utc", "fake_t", "fake_tn",

    "constants"
]

def __getattr__(name):
    if name == "Babel":
        from .babel import Babel
        return Babel

    if name == "Domain":
        from .domain import Domain
        return Domain

    if name == "Translations":
        from .translations import MergedTranslations
        return MergedTranslations

    if name == "I18nMessage":
        from .translations import I18nMessage
        return I18nMessage

    if name == "LazyString":
        from .speaklater import LazyString
        return LazyString

    if name in {
        "translation_resolver", "parse_best_match", "load_locale", "get_locale",
        "get_timezone", "format_message", "format_datetime", "format_date", "format_time",
        "format_timedelta", "format_number", "format_decimal", "format_percent", "format_currency",
        "format_scientific", "to_user_timezone", "to_utc", "fake_t", "fake_tn"
    }:
        from . import utils
        return getattr(utils, name)

    raise AttributeError(name)
