from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid.extensions.babel.babel import Babel
    from webfluid.extensions.babel.domain import Domain
    from webfluid.extensions.babel.translations import (
        MergedTranslations as Translations, I18nMessage
    )
    from webfluid.extensions.babel.speaklater import LazyString

__all__ = [
    "Babel", "Domain",
    "Translations", "I18nMessage",
    "LazyString",
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

    raise AttributeError(name)
