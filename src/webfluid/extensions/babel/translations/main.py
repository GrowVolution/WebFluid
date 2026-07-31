from babel.support import Translations

from .data import TransactionService


class MergedTranslations(Translations):
    def __init__(self, wrapped, locale, domain):
        super().__init__()
        self._wrapped = wrapped
        self._locale = locale
        self._domain = domain
        self._transaction_service = TransactionService(locale, domain)

    def _mo_get(self, message):
        return self._wrapped.gettext(message)

    def _mo_nget(self, singular, plural, n):
        return self._wrapped.ngettext(singular, plural, n)

    def _mo_pget(self, context, message):
        return self._wrapped.pgettext(context, message)

    def _mo_pnget(self, context, singular, plural, num):
        return self._wrapped.npgettext(context, singular, plural, num)

    def gettext(self, message):
        db_val = self._transaction_service.get(message)
        if db_val: return db_val
        return self._mo_get(message)

    def ngettext(self, msgid1, msgid2, n):
        db_val = self._transaction_service.get(msgid1, n)
        if db_val: return db_val
        return self._mo_nget(msgid1, msgid2, n)

    def pgettext(self, context, message):
        db_val = self._transaction_service.get(message, ctx=context)
        if db_val: return db_val
        return self._mo_pget(context, message)

    def npgettext(self, context, singular, plural, num):
        db_val = self._transaction_service.get(singular, num, context)
        if db_val: return db_val
        return self._mo_pnget(context, singular, plural, num)

    async def agettext(self, message):
        db_val = await self._transaction_service.aget(message)
        if db_val: return db_val
        return self._mo_get(message)

    async def angettext(self, msgid1, msgid2, n):
        db_val = await self._transaction_service.aget(msgid1, n)
        if db_val: return db_val
        return self._mo_nget(msgid1, msgid2, n)

    async def apgettext(self, context, message):
        db_val = await self._transaction_service.aget(message, ctx=context)
        if db_val: return db_val
        return self._mo_pget(context, message)

    async def anpgettext(self, context, singular, plural, num):
        db_val = await self._transaction_service.aget(singular, num, context)
        if db_val: return db_val
        return self._mo_pnget(context, singular, plural, num)

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
