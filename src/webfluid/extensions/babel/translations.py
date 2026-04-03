from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import UniqueConstraint, select
from babel.support import Translations
import asyncio

from webfluid.core.ext import db, babel
from webfluid.utils.logging import factory as log_factory


def _plural_key(locale: str, key: str, num: int) -> str:
    lc = babel.load_locale(locale)
    return f"{lc.plural_form(num)}:{key}"


class I18nMessage(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    locale: Mapped[str]
    domain: Mapped[str] = mapped_column(default="messages")
    key: Mapped[str]
    text: Mapped[str]
    ctx: Mapped[str | None]

    __table_args__ = (UniqueConstraint("locale", "domain", "key", "ctx"),)

    def __init__(self, locale: str, domain: str, key: str, text: str,
                 ctx: str | None = None):
        self.locale = locale
        self.domain = domain
        self.key = key
        self.text = text
        if ctx is not None: self.ctx = ctx


class MergedTranslations(Translations):
    _locks = {}
    _db_cache = {}

    def __init__(self, wrapped: Translations, locale: str, domain: str):
        super().__init__()
        self._wrapped = wrapped
        self._locale = locale
        self._domain = domain

    def _db_get(self, key: str, num: int = 1, ctx: str = None) -> str | None:
        locale_cache = MergedTranslations.cache(self._locale)
        if not locale_cache: return None

        domain_cache = locale_cache.get(self._domain)
        if not domain_cache: return None

        key = _plural_key(self._locale, key, num)
        key_cache = domain_cache.get(key)
        if not key_cache: return None

        ctx = ctx or ""
        return key_cache.get(ctx)

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
        db_val = self._db_get(singular, n)
        if db_val: return db_val
        return self._mo_nget(singular, plural, n)

    def pgettext(self, context: str, message: str) -> str | object:
        db_val = self._db_get(message, ctx=context)
        if db_val: return db_val
        return self._mo_pget(context, message)

    def npgettext(self, context: str, singular: str, plural: str, num: int) -> str:
        db_val = self._db_get(singular, num, context)
        if db_val: return db_val
        return self._mo_pnget(context, singular, plural, num)

    async def settext(self, key: str, message: str):
        await MergedTranslations._set(self._locale, self._domain, key, message)

    async def nsettext(self, key: str, message: str, num: int):
        await MergedTranslations._set(self._locale, self._domain, key, message, num)

    async def psettext(self, key: str, message: str, context: str):
        await MergedTranslations._set(self._locale, self._domain, key, message, ctx=context)

    async def npsettext(self, key: str, message: str, num: int, context: str):
        await MergedTranslations._set(self._locale, self._domain, key, message, num, context)

    @classmethod
    async def _set(cls, locale: str, domain: str, key: str, message: str,
                   num: int = 1, ctx: str = None):
        lock = cls._ensure_cache_and_lock(locale, domain)
        async with lock:
            async with db.async_executor(model=I18nMessage) as e:
                key = _plural_key(locale, key, num)

                result = await e.exec(
                    select(I18nMessage).where(
                        I18nMessage.locale == locale,
                        I18nMessage.domain == domain,
                        I18nMessage.key == key,
                        I18nMessage.ctx == ctx
                    )
                )

                row = result.first()
                if row:
                    row.text = message
                else:
                    await e.insert(I18nMessage(
                        locale, domain,
                        key, message, ctx
                    ))

            if key not in cls._db_cache[locale][domain]:
                cls._db_cache[locale][domain][key] = {}

            ctx = ctx or ""
            cls._db_cache[locale][domain][key][ctx] = message

    @classmethod
    def _ensure_cache_and_lock(cls, locale: str, domain: str) -> asyncio.Lock:
        if locale not in cls._db_cache:
            cls._db_cache[locale] = {}

        if domain not in cls._db_cache[locale]:
            cls._db_cache[locale][domain] = {}

        if locale not in cls._locks:
            cls._locks[locale] = {}

        return cls._locks[locale].setdefault(
            domain, asyncio.Lock()
        )

    @classmethod
    def cache(cls, locale: str) -> dict | None:
        locale_cache = cls._db_cache.get(locale)
        return locale_cache

    @classmethod
    async def db_load(cls, locale: str, domain: str):
        if (
                locale in cls._db_cache
                and domain in cls._db_cache[locale]
        ):
            return

        lock = cls._ensure_cache_and_lock(domain, locale)

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
                    if r.key not in new_cache:
                        new_cache[r.key] = {}

                    ctx = r.ctx or ""
                    new_cache[r.key][ctx] = r.text

            cls._db_cache[locale][domain] = new_cache

    @classmethod
    async def update(cls, domain: str, translations: dict):
        async with db.async_executor(model=I18nMessage) as e:
            for locale, keys in translations.items():

                lock = cls._ensure_cache_and_lock(domain, locale)
                async with lock:

                    new_cache = cls._db_cache[domain][locale]
                    for key, forms in keys.items():
                        for data, msg in forms.items():
                            key = f"{data[0]}:{key}"
                            if key not in new_cache:
                                new_cache[key] = {}

                            if not msg:
                                log_factory.warning(
                                    "[Babel] Missing message for "
                                    f"locale '{locale}' and key '{key}' "
                                    f"at domain '{domain}'."
                                )
                                continue

                            ctx = data[1] if len(data) > 1 else None

                            result = await e.exec(
                                select(I18nMessage).where(
                                    I18nMessage.locale == locale,
                                    I18nMessage.domain == domain,
                                    I18nMessage.key == key,
                                    I18nMessage.ctx == ctx,
                                )
                            )

                            row = result.first()
                            if row:
                                row.text = msg
                            else:
                                await e.insert(I18nMessage(
                                    locale, domain,
                                    key, msg, ctx
                                ))

                            ctx = ctx or ""
                            new_cache[key][ctx] = msg

                    cls._db_cache[locale][domain] = new_cache
