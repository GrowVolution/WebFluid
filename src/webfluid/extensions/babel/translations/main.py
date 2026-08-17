from babel.support import Translations

from .data import TransactionService

_CONTEXT = "%s\x04%s"


class MergedTranslations(Translations):
    def __init__(self, wrapped, locale, domain):
        super().__init__()
        self._wrapped = wrapped
        self._locale = locale
        self._domain = domain
        self._transaction_service = TransactionService(locale, domain)

    def _mo_has(self, key):
        return key in getattr(self._wrapped, "_catalog", ())

    def _mo_get(self, message):
        return self._wrapped.gettext(message)

    def _mo_nget(self, singular, plural, n):
        return self._wrapped.ngettext(singular, plural, n)

    def _mo_pget(self, context, message):
        return self._wrapped.pgettext(context, message)

    def _mo_pnget(self, context, singular, plural, num):
        return self._wrapped.npgettext(context, singular, plural, num)

    def findtext(self, message):
        db_val = self._transaction_service.get(message)
        if db_val: return db_val
        if self._mo_has(message): return self._mo_get(message)
        return None

    def nfindtext(self, msgid1, msgid2, n):
        db_val = self._transaction_service.get(msgid1, n)
        if db_val: return db_val
        if self._mo_has((msgid1, 0)): return self._mo_nget(msgid1, msgid2, n)
        return None

    def pfindtext(self, context, message):
        db_val = self._transaction_service.get(message, ctx=context)
        if db_val: return db_val
        if self._mo_has(_CONTEXT % (context, message)):
            return self._mo_pget(context, message)
        return None

    def npfindtext(self, context, singular, plural, num):
        db_val = self._transaction_service.get(singular, num, context)
        if db_val: return db_val
        if self._mo_has((_CONTEXT % (context, singular), 0)):
            return self._mo_pnget(context, singular, plural, num)
        return None

    async def afindtext(self, message):
        db_val = await self._transaction_service.aget(message)
        if db_val: return db_val
        if self._mo_has(message): return self._mo_get(message)
        return None

    async def anfindtext(self, msgid1, msgid2, n):
        db_val = await self._transaction_service.aget(msgid1, n)
        if db_val: return db_val
        if self._mo_has((msgid1, 0)): return self._mo_nget(msgid1, msgid2, n)
        return None

    async def apfindtext(self, context, message):
        db_val = await self._transaction_service.aget(message, ctx=context)
        if db_val: return db_val
        if self._mo_has(_CONTEXT % (context, message)):
            return self._mo_pget(context, message)
        return None

    async def anpfindtext(self, context, singular, plural, num):
        db_val = await self._transaction_service.aget(singular, num, context)
        if db_val: return db_val
        if self._mo_has((_CONTEXT % (context, singular), 0)):
            return self._mo_pnget(context, singular, plural, num)
        return None

    def gettext(self, message):
        found = self.findtext(message)
        return self._mo_get(message) if found is None else found

    def ngettext(self, msgid1, msgid2, n):
        found = self.nfindtext(msgid1, msgid2, n)
        return self._mo_nget(msgid1, msgid2, n) if found is None else found

    def pgettext(self, context, message):
        found = self.pfindtext(context, message)
        return self._mo_pget(context, message) if found is None else found

    def npgettext(self, context, singular, plural, num):
        found = self.npfindtext(context, singular, plural, num)
        if found is None: return self._mo_pnget(context, singular, plural, num)
        return found

    async def agettext(self, message):
        found = await self.afindtext(message)
        return self._mo_get(message) if found is None else found

    async def angettext(self, msgid1, msgid2, n):
        found = await self.anfindtext(msgid1, msgid2, n)
        return self._mo_nget(msgid1, msgid2, n) if found is None else found

    async def apgettext(self, context, message):
        found = await self.apfindtext(context, message)
        return self._mo_pget(context, message) if found is None else found

    async def anpgettext(self, context, singular, plural, num):
        found = await self.anpfindtext(context, singular, plural, num)
        if found is None: return self._mo_pnget(context, singular, plural, num)
        return found

    async def settext(self, key, message):
        await TransactionService.set(self._locale, self._domain, key, message, "one", None)

    async def nsettext(self, key, message, pf):
        await TransactionService.set(self._locale, self._domain, key, message, pf, None)

    async def psettext(self, key, message, context):
        await TransactionService.set(self._locale, self._domain, key, message, "one", context)

    async def npsettext(self, key, message, pf, context):
        await TransactionService.set(self._locale, self._domain, key, message, pf, context)

    async def uncache(self, key):
        await self._transaction_service.uncache(key)

    async def recache(self, key):
        await self._transaction_service.recache(key)
