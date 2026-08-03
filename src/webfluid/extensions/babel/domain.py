from babel import support
import os

from webfluid.core.context import FluidContext
from webfluid.extensions.babel.translations import MergedTranslations
from webfluid.extensions.babel.utils import get_locale


class Domain:
    def __init__(self, dir_path=None, domain="messages"):
        self.dir = dir_path
        self.domain = domain

        self.cache = {}

    def get_translations_path(self, fluid):
        if fluid: return self.dir or os.path.join(str(fluid.project_root), "translations")
        return self.dir or os.path.join(os.getcwd(), "translations")

    def get_translations(self):
        locale = get_locale()

        translations = self.cache.get(str(locale))
        if translations is None:
            ctx = FluidContext.try_current()
            dirname = self.get_translations_path(ctx.fluid if ctx is not None else None)
            wrapped = support.Translations.load(
                dirname, locale, domain=self.domain
            )
            translations = MergedTranslations(wrapped, str(locale), self.domain)
            self.cache[str(locale)] = translations

        return translations
