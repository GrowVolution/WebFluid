from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import UniqueConstraint, select
from babel.support import Translations
import asyncio

from webfluid.core.ext import db
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

    def __init__(self, domain: str, locale: str, key: str, text: str,
                 num: int = 1, ctx: str | None = None):
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
    _locks = {}
    _db_cache = {}

    def __init__(self, wrapped: Translations, domain: str, locale: str):
        super().__init__()
        self._wrapped = wrapped
        self._domain = domain
        self._locale = locale

    def _db_get(self, message: str, num: int = 1, ctx: str = None) -> str | None:
        domain_cache = self._db_cache.get(self._domain)
        if not domain_cache: return None

        locale_cache = domain_cache.get(self._locale)
        if not locale_cache: return None

        ctx = ctx or ""
        ctx_cache = locale_cache.get(ctx)
        if not ctx_cache: return None

        num_cache = ctx_cache.get(num)
        if not num_cache: return None

        return num_cache.get(message)

    def _mo_get(self, message: str) -> str | None:
        return self._wrapped.gettext(message)

    def _mo_nget(self, singular: str, plural: str, n: int) -> str | None:
        return self._wrapped.ngettext(singular, plural, n)

    def _mo_pget(self, context: str, message: str) -> str | object:
        return self._wrapped.pgettext(context, message)

    def _mo_pnget(self, context: str, singular: str, plural: str, num: int) -> str:
        return self._wrapped.npgettext(context, singular, plural, num)

    def gettext(self, message: str) -> str:
        db_val = self._db_get(message)
        if db_val: return db_val
        return self._mo_get(message)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        key = plural if n != 1 else singular
        db_val = self._db_get(key, n)
        if db_val: return db_val
        return self._mo_nget(singular, plural, n)

    def pgettext(self, context: str, message: str) -> str | object:
        db_val = self._db_get(message, ctx=context)
        if db_val: return db_val
        return self._mo_pget(context, message)

    def npgettext(self, context: str, singular: str, plural: str, num: int) -> str:
        key = plural if num != 1 else singular
        db_val = self._db_get(key, num, context)
        if db_val: return db_val
        return self._mo_pnget(context, singular, plural, num)

    @classmethod
    async def update_cache(cls, domain: str, locale: str):
        if (
                domain in cls._db_cache
                and locale in cls._db_cache[domain]
        ):
            return

        if domain not in cls._locks:
            cls._locks[domain] = {}
        if domain not in cls._db_cache:
            cls._db_cache[domain] = {}

        lock = cls._locks[domain].setdefault(
            locale, asyncio.Lock()
        )

        async with lock:
            async with db.async_executor(model=I18nMessage) as e:
                results = await e.exec(
                    select(I18nMessage)
                    .where(
                        I18nMessage.domain == domain,
                        I18nMessage.locale == locale,
                        )
                )
                rows = results.all()

                new_cache = {}
                for r in rows:
                    ctx = r.ctx or ""
                    if r.ctx not in new_cache:
                        new_cache[ctx] = {}
                    if r.num not in new_cache[ctx]:
                        new_cache[ctx][r.num] = {}
                    new_cache[ctx][r.num][r.key] = r.text

            cls._db_cache[domain][locale] = new_cache
