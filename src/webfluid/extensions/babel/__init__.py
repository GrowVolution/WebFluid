
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
