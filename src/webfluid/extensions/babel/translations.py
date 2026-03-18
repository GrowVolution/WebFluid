from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import UniqueConstraint, select
from babel.support import Translations

from webfluid.core.ext import db
from webfluid.utils import run_in_executor
from webfluid.exceptions import FrameworkException


class I18nMessage(db.Model):
    __bind_set__ = False

    id: Mapped[int] = mapped_column(primary_key=True)
    domain: Mapped[str] = mapped_column(nullable=False, default="messages")
    locale: Mapped[str] = mapped_column(nullable=False)
    key: Mapped[str] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(nullable=False)
    num: Mapped[int] = mapped_column(nullable=False)
    ctx: Mapped[str | None]

    __table_args__ = (UniqueConstraint("domain", "locale", "key", "num", "ctx"),)

    def __init__(self, domain, locale, key, text, num=1, ctx=None):
        self.domain = domain
        self.locale = locale
        self.key = key
        self.text = text
        self.num = num
        if ctx is not None: self.ctx = ctx

    @classmethod
    def set_bind(cls, key: str):
        if cls.__bind_set__:
            raise FrameworkException("Translation DB bind has already been set!")
        cls.__bind_key__ = key
        cls.__bind_set__ = True


class MergedTranslations(Translations):
    def __init__(self, wrapped: Translations, domain: str, locale: str):
        super().__init__()
        self._wrapped = wrapped
        self._domain = domain
        self._locale = locale

    def _db_get(self, message: str, num: int = 1, ctx: str = None) -> str | None:
        with db.executor(model=I18nMessage) as e:
            row = e.exec(
                select(I18nMessage)
                .where(
                    I18nMessage.domain == self._domain,
                    I18nMessage.locale == self._locale,
                    I18nMessage.key == message,
                    I18nMessage.num == num,
                    I18nMessage.ctx == ctx
                )
            ).first()
        return row.text if row else None

    async def _db_aget(self, message: str, num: int = 1, ctx: str = None) -> str | None:
        async with db.async_executor(model=I18nMessage) as e:
            row = await e.exec_async(
                select(I18nMessage)
                .where(
                    I18nMessage.domain == self._domain,
                    I18nMessage.locale == self._locale,
                    I18nMessage.key == message,
                    I18nMessage.num == num,
                    I18nMessage.ctx == ctx
                )
            ).first()
        return row.text if row else None

    def _mo_get(self, message: str) -> str | None:
        return self._wrapped.gettext(message)

    async def _mo_aget(self, message: str) -> str | None:
        return await run_in_executor(self._mo_get, message)

    def _mo_nget(self, singular: str, plural: str, n: int) -> str | None:
        return self._wrapped.ngettext(singular, plural, n)

    async def _mo_anget(self, singular: str, plural: str, n: int) -> str | None:
        return await run_in_executor(self._mo_nget, singular, plural, n)

    def _mo_pget(self, context: str, message: str) -> str | object:
        return self._wrapped.pgettext(context, message)

    async def _mo_apget(self, context: str, message: str) -> str | object:
        return await run_in_executor(self._mo_pget, context, message)

    def _mo_pnget(self, context: str, singular: str, plural: str, num: int) -> str:
        return self._wrapped.npgettext(context, singular, plural, num)

    async def _mo_apnget(self, context: str, singular: str, plural: str, num: int) -> str:
        return await run_in_executor(self._mo_pnget, context, singular, plural, num)

    def gettext(self, message: str) -> str:
        db_val = self._db_get(message)
        if db_val: return db_val
        return self._mo_get(message)

    async def agettext(self, message: str) -> str:
        db_val = await self._db_aget(message)
        if db_val: return db_val
        return await self._mo_aget(message)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        key = plural if n != 1 else singular
        db_val = self._db_get(key, n)
        if db_val: return db_val
        return self._mo_nget(singular, plural, n)

    async def angettext(self, singular: str, plural: str, n: int) -> str:
        key = plural if n != 1 else singular
        db_val = await self._db_aget(key, n)
        if db_val: return db_val
        return await self._mo_anget(singular, plural, n)

    def pgettext(self, context: str, message: str) -> str | object:
        db_val = self._db_get(message, ctx=context)
        if db_val: return db_val
        return self._mo_pget(context, message)

    async def apgettext(self, context: str, message: str) -> str | object:
        db_val = await self._db_aget(message, ctx=context)
        if db_val: return db_val
        return await self._mo_apget(context, message)

    def npgettext(self, context: str, singular: str, plural: str, num: int) -> str:
        key = plural if num != 1 else singular
        db_val = self._db_get(key, num, context)
        if db_val: return db_val
        return self._mo_pnget(context, singular, plural, num)

    async def anpgettext(self, context: str, singular: str, plural: str, num: int) -> str:
        key = plural if num != 1 else singular
        db_val = await self._db_aget(key, num, context)
        if db_val: return db_val
        return await self._mo_apnget(context, singular, plural, num)
