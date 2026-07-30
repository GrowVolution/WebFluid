import json


class Cache:
    _db_cache = {}
    _uncached = {}

    def __init__(self, locale, domain):
        self._locale = locale
        self._domain = domain

    def is_uncached(self, key):
        return key in Cache._uncached.get(self._domain, ())

    def get(self, key, num, ctx):
        locale_cache = Cache.locale_cache(self._locale)
        if not locale_cache: return None

        domain_cache = locale_cache.get(self._domain)
        if not domain_cache: return None

        key_cache = domain_cache.get(key)
        if not key_cache: return None

        from .plural import plural_form
        pf_cache = key_cache.get(plural_form(self._locale, num))
        if not pf_cache: return None

        return pf_cache.get(ctx or "")

    async def uncache(self, key, lock):
        Cache._uncached.setdefault(self._domain, set()).add(key)

        for locale in list(Cache._db_cache):
            if self._domain not in Cache._db_cache[locale]: continue

            async with lock(locale, self._domain):
                Cache._ensure_cache(locale, self._domain)
                Cache._db_cache[locale][self._domain].pop(key, None)

    async def recache(self, key, by_locale, lock):
        for locale, entries in by_locale.items():
            if locale not in Cache._db_cache \
                    or self._domain not in Cache._db_cache[locale]:
                continue

            async with lock(locale, self._domain):
                Cache._ensure_cache(locale, self._domain)
                key_cache = Cache._db_cache[locale][
                    self._domain].setdefault(key, {})

                for pf, ctx, text in entries:
                    key_cache.setdefault(pf, {})[ctx or ""] = text

        if self._domain in Cache._uncached:
            Cache._uncached[self._domain].discard(key)

    @classmethod
    def _ensure_cache(cls, locale, domain):
        if locale not in cls._db_cache:
            cls._db_cache[locale] = {}

        if domain not in cls._db_cache[locale]:
            cls._db_cache[locale][domain] = {}

    @classmethod
    def already_loaded(cls, locale, domain):
        return (
            locale in cls._db_cache
            and domain in cls._db_cache[locale]
        )

    @classmethod
    def set(cls, locale, domain, key, message, pf, ctx):
        cls._ensure_cache(locale, domain)

        if key in cls._uncached.get(domain, ()):
            return

        cls._db_cache[locale][domain].setdefault(
            key, {}).setdefault(pf, {})[ctx or ""] = message

    @classmethod
    def locale_cache(cls, locale):
        return cls._db_cache.get(locale)

    @classmethod
    def db_load(cls, locale, domain, messages):
        if cls.already_loaded(locale, domain): return

        cache = {}
        uncached = cls._uncached.setdefault(domain, set())
        cls._ensure_cache(locale, domain)

        for msg in messages:
            if not msg.key.cached:
                uncached.add(msg.key.key)
                continue

            if msg.key.key not in cache:
                cache[msg.key.key] = {}

            if msg.pf not in cache[msg.key.key]:
                cache[msg.key.key][msg.pf] = {}

            cache[msg.key.key][msg.pf][msg.ctx or ""] = msg.text

        cls._db_cache[locale][domain] = cache

    @classmethod
    def update(cls, locale, domain, keys):
        cls._ensure_cache(locale, domain)
        new_cache = cls._db_cache[locale][domain]
        uncached = cls._uncached.get(domain, ())

        for key, forms in keys.items():
            for data, msg in forms.items():
                if not msg: continue
                data = json.loads(data)
                pf = data.get("pf", "one")
                ctx = data.get("ctx")

                if key in uncached: continue

                if key not in new_cache:
                    new_cache[key] = {}

                if pf not in new_cache[key]:
                    new_cache[key][pf] = {}

                new_cache[key][pf][ctx or ""] = msg

        cls._db_cache[locale][domain] = new_cache
