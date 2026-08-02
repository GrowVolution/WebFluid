from sqlalchemy import select
from sqlalchemy.orm import contains_eager
from sqlalchemy.exc import OperationalError
import asyncio, json

from .caching import Cache
from .models import I18nKey, I18nMessage
from .plural import plural_form
from webfluid.core.ext import db
from webfluid.utils.logging import factory as log_factory


async def _retry_locked(fn, *, attempts=6, delay=0.1):
    for i in range(attempts):
        try: return await fn()
        except OperationalError as e:
            if "database is locked" not in str(e).lower() or i == attempts - 1:
                raise
            log_factory.warning(
                f"[Babel] Database locked, retrying ({i + 1}/{attempts - 1})."
            )
            await asyncio.sleep(delay * (2 ** i))

    return None


async def _write(e, locale, kid, msg, pf, ctx):
    with e.session.no_autoflush:
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


class TransactionService:
    _locks = {}

    def __init__(self, locale, domain):
        self._locale = locale
        self._domain = domain
        self._cache = Cache(locale, domain)

    def _fetch(self, key, num, ctx):
        pf = plural_form(self._locale, num)

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

    async def _afetch(self, key, num, ctx):
        pf = plural_form(self._locale, num)

        async with db.async_executor(model=I18nMessage) as e:
            result = await e.exec(
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

    def get(self, key, num=1, ctx=None):
        if self._cache.is_uncached(key):
            return self._fetch(key, num, ctx)
        return self._cache.get(key, num, ctx)

    async def aget(self, key, num=1, ctx=None):
        if self._cache.is_uncached(key):
            return await self._afetch(key, num, ctx)
        return self._cache.get(key, num, ctx)

    async def uncache(self, key):
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

        await self._cache.uncache(key, TransactionService._ensure_lock)

    async def recache(self, key):
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
                
        await self._cache.recache(key, by_locale, TransactionService._ensure_lock)

    @classmethod
    def _ensure_lock(cls, locale, domain):
        if locale not in cls._locks:
            cls._locks[locale] = {}

        return cls._locks[locale].setdefault(
            domain, asyncio.Lock()
        )

    @classmethod
    async def kid(cls, domain, key):
        async def run():
            async with db.async_executor(model=I18nKey) as e:
                result = await e.exec(select(I18nKey).where(
                    I18nKey.key == key, I18nKey.domain == domain
                ))
                row = result.first()
                if row: return row.id

                await e.insert(I18nKey(key, domain))

                result = await e.exec(select(I18nKey).where(
                    I18nKey.key == key, I18nKey.domain == domain
                ))
                return result.first().id

        return await _retry_locked(run)

    @classmethod
    async def resolve_keys(cls, domain, keys):
        async def run():
            kids = {}

            async with db.async_executor(model=I18nKey) as e:
                result = await e.exec(select(I18nKey).where(
                    I18nKey.key.in_(keys), I18nKey.domain == domain
                ))
                for row in result.all(): kids[row.key] = row.id

                missing = [k for k in keys if k not in kids]
                for k in missing: await e.insert(I18nKey(k, domain))

                if missing:
                    result = await e.exec(select(I18nKey).where(
                        I18nKey.key.in_(missing), I18nKey.domain == domain
                    ))
                    for row in result.all(): kids[row.key] = row.id

            return kids

        return await _retry_locked(run)

    @classmethod
    async def set(cls, locale, domain, key, message, pf, ctx):
        kid = await cls.kid(domain, key)
        lock = cls._ensure_lock(locale, domain)

        async with lock:
            async def write():
                async with db.async_executor(model=I18nMessage) as e:
                    await _write(e, locale, kid, message, pf, ctx)

            await _retry_locked(write)
            Cache.set(locale, domain, key, message, pf, ctx)

    @classmethod
    async def load(cls, locale, domain):
        if Cache.already_loaded(locale, domain): return
        lock = cls._ensure_lock(locale, domain)

        async with lock:
            async def read():
                async with db.async_executor(model=I18nMessage) as e:
                    results = await e.exec(
                        select(I18nMessage)
                        .join(I18nMessage.key)
                        .where(
                            I18nMessage.locale == locale,
                            I18nKey.domain == domain
                        )
                        .options(contains_eager(I18nMessage.key))
                    )

                    Cache.db_load(locale, domain, results.all())

            await _retry_locked(read)

    @classmethod
    async def update(cls, domain, translations):
        translations = translations()

        all_keys = set()
        for keys in translations.values():
            all_keys.update(keys.keys())

        kids = await cls.resolve_keys(domain, all_keys)

        for locale, keys in translations.items():

            lock = cls._ensure_lock(locale, domain)
            async with lock:
                async def write():
                    async with db.async_executor(model=I18nMessage) as e:
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

                                await _write(e, locale, kid, msg, pf, ctx)

                await _retry_locked(write)
                Cache.update(locale, domain, keys)
