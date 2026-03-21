from babel import support
from typing import TYPE_CHECKING, Any
import os

from webfluid.core.context import FluidContext
from webfluid.extensions.babel.translations import MergedTranslations
from webfluid.extensions.babel.speaklater import LazyString
from webfluid.extensions.utils.babel import get_locale

if TYPE_CHECKING:
    from webfluid.core.fluid import Fluid
    from os import PathLike


class Domain:
    def __init__(self, dir_path: "str | PathLike[str] | None" = None, domain: str = "messages"):
        self.dir = dir_path
        self.domain = domain

        self.cache: dict[str, MergedTranslations] = {}

    def get_translations_path(self, fluid: "Fluid | None") -> "PathLike[str] | str":
        if fluid: return self.dir or os.path.join(str(fluid.app_root), "translations")
        return self.dir or os.path.join(os.getcwd(), "translations")

    def get_translations(self) -> MergedTranslations:
        locale = get_locale()

        translations = self.cache.get(str(locale))
        if translations is None:
            try: ctx = FluidContext.current()
            except RuntimeError: ctx = None

            dirname = self.get_translations_path(ctx.fluid if ctx else None)
            wrapped = support.Translations.load(
                dirname, locale, domain=self.domain
            )
            translations = MergedTranslations(wrapped, self.domain, str(locale))
            self.cache[str(locale)] = translations

        return translations

    def gettext(self, string: str, **variables: Any):
        t = self.get_translations()
        if variables:  return t.gettext(string) % variables
        return t.gettext(string)

    def ngettext(self, singular: str, plural: str, num: int, **variables: Any):
        variables.setdefault("num", num)
        t = self.get_translations()
        return t.ngettext(singular, plural, num) % variables

    def pgettext(self, context: str, string: str, **variables: Any):
        t = self.get_translations()
        if variables:
            return t.pgettext(context, string) % variables
        return t.pgettext(context, string)

    def npgettext(
            self, context: str, singular: str, plural: str, num: int, **variables: Any
    ):
        variables.setdefault("num", num)
        t = self.get_translations()
        return t.npgettext(context, singular, plural, num) % variables

    def lazy_gettext(self, string: str, **variables: Any):
        return LazyString(self.gettext, string, **variables)

    def lazy_ngettext(self, singular: str, plural: str, num: int, **variables: Any):
        return LazyString(self.ngettext, singular, plural, num, **variables)

    def lazy_pgettext(self, context: str, string: str, **variables: Any):
        return LazyString(self.pgettext, context, string, **variables)

    def lazy_npgettext(self, context: str, singular: str, plural: str, num: int, **variables: Any):
        return LazyString(self.npgettext, context, singular, plural, num, **variables)
