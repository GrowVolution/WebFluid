from .domains import Domains
from .translations import Translations
from .selection import Selector
from webfluid.core.identity import FRAMEWORK_ID
from webfluid.extensions.babel.speaklater import LazyString
from webfluid.extensions.babel.utils import format_message


class Translator:
    def __init__(self, default_domain, disable_update):
        self.domains = Domains(default_domain)
        self.translations = Translations(disable_update)
        self.selector = Selector()

    def gettext(self, string, **variables):
        for domain in self._fallback_escalation:
            t = domain.get_translations()

            msg = t.findtext(string)
            if msg is not None:
                return format_message(msg, **variables)

        return format_message(string, **variables)

    def ngettext(self, singular, plural, num, **variables):
        variables.setdefault("num", num)

        for domain in self._fallback_escalation:
            t = domain.get_translations()

            msg = t.nfindtext(singular, plural, num)
            if msg is not None:
                return format_message(msg, **variables)

        return format_message(singular if num == 1 else plural, **variables)

    def pgettext(self, context, string, **variables):
        for domain in self._fallback_escalation:
            t = domain.get_translations()

            msg = t.pfindtext(context, string)
            if msg is not None:
                return format_message(msg, **variables)

        return self.gettext(string, **variables)

    def npgettext(self, context, singular, plural, num, **variables):
        variables.setdefault("num", num)

        for domain in self._fallback_escalation:
            t = domain.get_translations()

            msg = t.npfindtext(context, singular, plural, num)
            if msg is not None:
                return format_message(msg, **variables)

        return self.ngettext(singular, plural, num, **variables)

    async def agettext(self, string, **variables):
        for domain in self._fallback_escalation:
            t = domain.get_translations()

            msg = await t.afindtext(string)
            if msg is not None:
                return format_message(msg, **variables)

        return format_message(string, **variables)

    async def angettext(self, singular, plural, num, **variables):
        variables.setdefault("num", num)

        for domain in self._fallback_escalation:
            t = domain.get_translations()

            msg = await t.anfindtext(singular, plural, num)
            if msg is not None:
                return format_message(msg, **variables)

        return format_message(singular if num == 1 else plural, **variables)

    async def apgettext(self, context, string, **variables):
        for domain in self._fallback_escalation:
            t = domain.get_translations()

            msg = await t.apfindtext(context, string)
            if msg is not None:
                return format_message(msg, **variables)

        return await self.agettext(string, **variables)

    async def anpgettext(self, context, singular, plural, num, **variables):
        variables.setdefault("num", num)

        for domain in self._fallback_escalation:
            t = domain.get_translations()

            msg = await t.anpfindtext(context, singular, plural, num)
            if msg is not None:
                return format_message(msg, **variables)

        return await self.angettext(singular, plural, num, **variables)

    def lazy_gettext(self, string, **variables):
        return LazyString(self.gettext, string, **variables)

    def lazy_ngettext(self, singular, plural, num, **variables):
        return LazyString(self.ngettext, singular, plural, num, **variables)

    def lazy_pgettext(self, context, string, **variables):
        return LazyString(self.pgettext, context, string, **variables)

    def lazy_npgettext(self, context, singular, plural, num, **variables):
        return LazyString(self.npgettext, context, singular, plural, num, **variables)

    @property
    def _fallback_escalation(self):
        current = self.domains.current_domain
        domains = [current]

        default = self.domains.default_domain
        if domains[0] != default:
            domains.append(default)

        store = self.domains.store
        if "__fallback__" in store:
            domains.append(store["__fallback__"])

        if FRAMEWORK_ID in store:
            domains.append(store[FRAMEWORK_ID])

        return domains
