from babel import support
from typing import Any, TYPE_CHECKING
import os

from webfluid.core.ext import babel
from webfluid.core.context import FluidContext
from webfluid.extensions.babel.translations import MergedTranslations
from webfluid.extensions.babel.speaklater import LazyString
from webfluid.extensions.utils.babel import get_locale

if TYPE_CHECKING:
    from webfluid import Fluid
    from os import PathLike


class Domain:
    def __init__(self, dir_path: "str | PathLike[str] | None" = None, domain: str = "messages"):
        self.dir = dir_path
        self.domain = domain

        self.cache: dict[str, MergedTranslations] = {}

    def get_translations_path(self, fluid: "Fluid | None") -> "PathLike[str] | str":
        if fluid: return self.dir or os.path.join(str(fluid.app.root_path), "translations")
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
        if variables:  return t.ugettext(string) % variables
        return t.ugettext(string)

    async def agettext(self, string: str, **variables: Any):
        t = self.get_translations()
        text = await t.agettext(string)
        if variables: return text % variables
        return text

    def ngettext(self, singular: str, plural: str, num: int, **variables: Any):
        variables.setdefault("num", num)
        t = self.get_translations()
        return t.ungettext(singular, plural, num) % variables

    async def angettext(self, singular: str, plural: str, num: int, **variables: Any):
        variables.setdefault("num", num)
        t = self.get_translations()
        text = await t.angettext(singular, plural, num)
        return text % variables

    def pgettext(self, context: str, string: str, **variables: Any):
        t = self.get_translations()
        if variables:
            return t.upgettext(context, string) % variables
        return t.upgettext(context, string)

    async def apgettext(self, context: str, string: str, **variables: Any):
        t = self.get_translations()
        text = await t.apgettext(context, string)
        if variables: return text % variables
        return text

    def npgettext(
            self, context: str, singular: str, plural: str, num: int, **variables: Any
    ):
        variables.setdefault("num", num)
        t = self.get_translations()
        return t.unpgettext(context, singular, plural, num) % variables

    async def anpgettext(
            self, context: str, singular: str, plural: str, num: int, **variables: Any
    ):
        variables.setdefault("num", num)
        t = self.get_translations()
        text = await t.anpgettext(context, singular, plural, num)
        return text % variables

    def lazy_gettext(self, string: str, **variables: Any):
        return LazyString(self.gettext, string, **variables)

    def lazy_ngettext(self, singular: str, plural: str, num: int, **variables: Any):
        return LazyString(self.ngettext, singular, plural, num, **variables)

    def lazy_pgettext(self, context: str, string: str, **variables: Any):
        return LazyString(self.pgettext, context, string, **variables)
