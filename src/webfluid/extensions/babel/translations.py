from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UniqueConstraint, ForeignKey, select
from babel.support import Translations
from typing import Optional, Callable
from functools import lru_cache
import asyncio, json

from webfluid.core.ext import db, babel
from webfluid.utils.logging import factory as log_factory


@lru_cache(maxsize=None)
def _plural_rule(locale: str):
    return babel.load_locale(locale).plural_form


def _plural_form(locale: str, num: int) -> str:
    return _plural_rule(locale)(num)


class I18nKey(db.Model):
    __tablename__ = "i18n_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(unique=True)
    domain: Mapped[str]
    cached: Mapped[bool]

    messages: Mapped[list[I18nMessage]] = relationship(
        back_populates="key",
        lazy="selectin"
    )

    def __init__(self, key: str, domain: str, cached: bool = True):
        self.key = key
        self.domain = domain
        self.cached = cached


class I18nMessage(db.Model):
    __tablename__ = "i18n"
    __table_args__ = (UniqueConstraint("locale", "kid", "pf", "ctx"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kid: Mapped[int] = mapped_column(ForeignKey("i18n_keys.id"))

    locale: Mapped[str]
    pf: Mapped[str]
    text: Mapped[str]
    ctx: Mapped[Optional[str]]

    key: Mapped[I18nKey] = relationship(
        back_populates="messages",
        lazy="selectin"
    )

    def __init__(self, kid: int, locale: str, text: str,
                 pf: str = "one", ctx: Optional[str] = None):
        self.kid = kid
        self.locale = locale
        self.pf = pf
        self.text = text
        if ctx is not None: self.ctx = ctx


class MergedTranslations(Translations):
    _locks = {}
    _db_cache = {}
    _uncached = {}

    def __init__(self, wrapped: Translations, locale: str, domain: str):
        super().__init__()
        self._wrapped = wrapped
        self._locale = locale
        self._domain = domain

    def _db_fetch(self, key: str, num: int = 1, ctx: Optional[str] = None) -> Optional[str]:
        pf = _plural_form(self._locale, num)

        with db.executor(model=I18nMessage) as e:
            result = e.exec(
                select(I18nMessage).where(
                    I18nMessage.locale == self._locale,
                    I18nMessage.pf == pf,
                    I18nMessage.ctx == ctx,
                    I18nMessage.key.has(
                        (I18nKey.key == key) & (I18nKey.domain == self._domain)
                    )
                )
            )
            row = result.first()
            return row.text if row else None

    def _db_get(self, key: str, num: int = 1, ctx: Optional[str] = None) -> str | None:
        if key in MergedTranslations._uncached.get(self._domain, ()):
            return self._db_fetch(key, num, ctx)

        locale_cache = MergedTranslations.cache(self._locale)
        if not locale_cache: return None

        domain_cache = locale_cache.get(self._domain)
        if not domain_cache: return None

        key_cache = domain_cache.get(key)
        if not key_cache: return None

        pf_cache = key_cache.get(_plural_form(self._locale, num))
        if not pf_cache: return None

        return pf_cache.get(ctx or "")

    def _mo_get(self, message: str) -> str:
        return self._wrapped.gettext(message)

    def _mo_nget(self, singular: str, plural: str, n: int) -> str:
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
        await MergedTranslations._set(self._locale, self._domain, key, message, "one", None)

    async def nsettext(self, key: str, message: str, pf: str):
        await MergedTranslations._set(self._locale, self._domain, key, message, pf, None)

    async def psettext(self, key: str, message: str, context: str):
        await MergedTranslations._set(self._locale, self._domain, key, message, "one", context)

    async def npsettext(self, key: str, message: str, pf: str, context: str):
        await MergedTranslations._set(self._locale, self._domain, key, message, pf, context)

    async def uncache(self, key: str):
        async with db.async_executor(model=I18nKey) as e:
            result = await e.exec(
                select(I18nKey).where(
                    I18nKey.key == key,
                    I18nKey.domain == self._domain
                )
            )
            row = result.first()
            if not row: return

            row.cached = False

        MergedTranslations._uncached.setdefault(self._domain, set()).add(key)

        for locale in list(MergedTranslations._db_cache):
            if self._domain not in MergedTranslations._db_cache[locale]: continue

            lock = MergedTranslations._ensure_cache_and_lock(locale, self._domain)
            async with lock:
                MergedTranslations._db_cache[locale][self._domain].pop(key, None)

    async def recache(self, key: str):
        async with db.async_executor(model=I18nKey) as e:
            result = await e.exec(
                select(I18nKey).where(
                    I18nKey.key == key,
                    I18nKey.domain == self._domain
                )
            )
            row = result.first()
            if not row: return

            row.cached = True
            kid = row.id

        by_locale = {}
        async with db.async_executor(model=I18nMessage) as e:
            result = await e.exec(select(I18nMessage).where(I18nMessage.kid == kid))
            for r in result.all():
                by_locale.setdefault(r.locale, []).append((r.pf, r.ctx, r.text))

        for locale, entries in by_locale.items():
            if locale not in MergedTranslations._db_cache \
                    or self._domain not in MergedTranslations._db_cache[locale]:
                continue

            lock = MergedTranslations._ensure_cache_and_lock(locale, self._domain)
            async with lock:
                key_cache = MergedTranslations._db_cache[locale][
                    self._domain].setdefault(key, {})

                for pf, ctx, text in entries:
                    key_cache.setdefault(pf, {})[ctx or ""] = text

        if self._domain in MergedTranslations._uncached:
            MergedTranslations._uncached[self._domain].discard(key)

    @classmethod
    async def _kid(cls, domain: str, key: str) -> int:
        async with db.async_executor(model=I18nKey) as e:
            result = await e.exec(select(I18nKey).where(I18nKey.key == key))
            row = result.first()
            if row: return row.id

            await e.insert(I18nKey(key, domain))

            result = await e.exec(select(I18nKey).where(I18nKey.key == key))
            return result.first().id

    @classmethod
    async def _resolve_keys(cls, domain: str, keys: set[str]) -> dict[str, int]:
        kids = {}

        async with db.async_executor(model=I18nKey) as e:
            result = await e.exec(select(I18nKey).where(I18nKey.key.in_(keys)))
            for row in result.all(): kids[row.key] = row.id

            missing = [k for k in keys if k not in kids]
            for k in missing: await e.insert(I18nKey(k, domain))

            if missing:
                result = await e.exec(select(I18nKey).where(
                    I18nKey.key.in_(missing)
                ))
                for row in result.all(): kids[row.key] = row.id

        return kids

    @classmethod
    async def _set(cls, locale: str, domain: str, key: str,
                   message: str, pf: str, ctx: Optional[str]):
        kid = await cls._kid(domain, key)

        lock = cls._ensure_cache_and_lock(locale, domain)
        async with lock:
            async with db.async_executor(model=I18nMessage) as e:
                result = await e.exec(
                    select(I18nMessage).where(
                        I18nMessage.locale == locale,
                        I18nMessage.kid == kid,
                        I18nMessage.pf == pf,
                        I18nMessage.ctx == ctx
                    )
                )

                row = result.first()
                if row: row.text = message
                else: await e.insert(
                    I18nMessage(kid, locale, message, pf, ctx)
                )

            if key in cls._uncached.get(domain, ()):
                return

            cls._db_cache[locale][domain].setdefault(
                key, {}).setdefault(pf, {})[ctx or ""] = message

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

        lock = cls._ensure_cache_and_lock(locale, domain)

        async with lock:
            async with db.async_executor(model=I18nMessage) as e:
                results = await e.exec(
                    select(I18nMessage).where(
                        I18nMessage.locale == locale,
                        I18nMessage.key.has(I18nKey.domain == domain)
                    )
                )
                rows = results.all()

                new_cache = {}
                uncached = cls._uncached.setdefault(domain, set())

                for msg in rows:
                    if not msg.key.cached:
                        uncached.add(msg.key.key)
                        continue

                    if msg.key.key not in new_cache:
                        new_cache[msg.key.key] = {}

                    if msg.pf not in new_cache[msg.key.key]:
                        new_cache[msg.key.key][msg.pf] = {}

                    new_cache[msg.key.key][msg.pf][msg.ctx or ""] = msg.text

            cls._db_cache[locale][domain] = new_cache

    @classmethod
    async def update(cls, domain: str,
                     translations: Callable[[], dict[
                         str, dict[
                             str, dict[
                                 tuple[str, str | None], str
                             ]
                         ]
                     ]]):
        translations = translations()

        all_keys = set()
        for keys in translations.values():
            all_keys.update(keys.keys())

        kids = await cls._resolve_keys(domain, all_keys)

        async with db.async_executor(model=I18nMessage) as e:
            for locale, keys in translations.items():

                lock = cls._ensure_cache_and_lock(locale, domain)
                async with lock:

                    new_cache = cls._db_cache[locale][domain]
                    uncached = cls._uncached.get(domain, ())

                    for key, forms in keys.items():
                        kid = kids[key]

                        for data, msg in forms.items():
                            data = json.loads(data)
                            pf = data.get("pf", "one")
                            ctx = data.get("ctx")

                            if not msg:
                                log_factory.warning(
                                    "[Babel] Missing message for "
                                    f"locale '{locale}' and key '{key}' "
                                    f"at domain '{domain}'."
                                )
                                continue

                            result = await e.exec(
                                select(I18nMessage).where(
                                    I18nMessage.locale == locale,
                                    I18nMessage.kid == kid,
                                    I18nMessage.pf == pf,
                                    I18nMessage.ctx == ctx
                                )
                            )

                            row = result.first()
                            if row: row.text = msg
                            else: await e.insert(
                                I18nMessage(kid, locale, msg, pf, ctx)
                            )

                            if key in uncached: continue

                            if key not in new_cache:
                                new_cache[key] = {}

                            if pf not in new_cache[key]:
                                new_cache[key][pf] = {}

                            new_cache[key][pf][ctx or ""] = msg
