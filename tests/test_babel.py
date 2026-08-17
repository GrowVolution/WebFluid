from types import SimpleNamespace
import json, os, pytest

os.environ.setdefault("EXT_SQLALCHEMY", "1")

from webfluid.core.ext import db
from webfluid.extensions.babel.babel.translation.main import Translator
from webfluid.extensions.babel.babel.translation.translations import Translations
from webfluid.extensions.babel.translations import (
    Cache, I18nKey, I18nMessage, MergedTranslations, TransactionService
)
from webfluid.extensions.sqlalchemy.bind import Bind
from webfluid.extensions.sqlalchemy.sqlalchemy import SQLAlchemy

LOCALE = "de"
DOMAIN = "messages"
ADMIN = "admin"


class Catalog:
    def __init__(self, messages=None):
        self.messages = messages or {}
        self._catalog = {}

        for key, value in self.messages.items():
            if isinstance(key, tuple): key = f"{key[0]}\x04{key[1]}"
            self._catalog[key] = value
            self._catalog[(key, 0)] = value

    def gettext(self, message):
        return self.messages.get(message, message)

    def ngettext(self, singular, plural, n):
        return self.messages.get(singular, singular if n == 1 else plural)

    def pgettext(self, context, message):
        return self.messages.get((context, message), message)

    def npgettext(self, context, singular, plural, num):
        return self.messages.get(
            (context, singular), singular if num == 1 else plural
        )


class Domain:
    def __init__(self, translations): self._translations = translations
    def get_translations(self): return self._translations


def bind_database(tmp_path):
    path = tmp_path / "i18n.db"
    bind = Bind("default", (f"sqlite:///{path}", f"sqlite+aiosqlite:///{path}"))

    db._binds["default"] = bind
    SQLAlchemy._instance = db
    db.Model.metadata.create_all(bind.sync_engine)

    Cache._uncached = {}
    Cache._db_cache = {}
    TransactionService._locks = {}

    return bind


def reset_database():
    db._binds.clear()
    SQLAlchemy._instance = None
    Cache._uncached = {}
    Cache._db_cache = {}
    TransactionService._locks = {}


@pytest.fixture
def bound(tmp_path):
    bind = bind_database(tmp_path)

    with bind.session() as session:
        key = I18nKey("greeting", DOMAIN, cached=False)
        session.add(key)
        session.flush()
        session.add(I18nMessage(key.id, LOCALE, "Moin"))

    Cache._uncached = { DOMAIN: {"greeting"} }

    yield
    reset_database()


@pytest.fixture
def catalog(tmp_path):
    bind = bind_database(tmp_path)

    with bind.session() as session:
        ids = {}
        for key, domain, cached in (
                ("greeting", DOMAIN, True),
                ("apples", DOMAIN, True),
                ("secret", DOMAIN, False),
                ("dashboard", ADMIN, True)
        ):
            row = I18nKey(key, domain, cached=cached)
            session.add(row)
            session.flush()
            ids[key] = row.id

        session.add_all([
            I18nMessage(ids["greeting"], LOCALE, "Moin"),
            I18nMessage(ids["greeting"], LOCALE, "Moin Chef", ctx="formal"),
            I18nMessage(ids["greeting"], "en", "Hi"),
            I18nMessage(ids["apples"], LOCALE, "ein Apfel"),
            I18nMessage(ids["apples"], LOCALE, "viele Aepfel", pf="other"),
            I18nMessage(ids["secret"], LOCALE, "geheim"),
            I18nMessage(ids["dashboard"], LOCALE, "Uebersicht")
        ])

    yield
    reset_database()


@pytest.fixture
def selection(monkeypatch):
    import webfluid.core.ext as ext

    monkeypatch.setattr(
        ext, "babel", SimpleNamespace(
            default_locale="en", supported_locales=("en", "de"),
            default_timezone="UTC",
            locale_selector_fn=None, timezone_selector_fn=None
        ), raising=False
    )


def uncached(*keys):
    Cache._uncached.setdefault(DOMAIN, set()).update(keys)


def request(query=None, cookies=None, headers=None):
    return SimpleNamespace(
        query_params=query or {}, cookies=cookies or {}, headers=headers or {}
    )


@pytest.mark.parametrize("source, expected", [
    (request(query={"lang": LOCALE}), LOCALE),
    (request(cookies={"lang": LOCALE}), LOCALE),
    (request(headers={"Accept-Language": "de-DE,de;q=0.9,en;q=0.8"}), LOCALE),
    (request(query={"lang": LOCALE}, cookies={"lang": "en"}), LOCALE),
    (request(), "en"),
    (None, "en")
])
def test_request_locale_follows_the_request(selection, source, expected):
    from webfluid.core.context import FluidContext
    from webfluid.extensions.babel.utils import _request_locale

    with FluidContext(None, source):
        assert str(_request_locale()) == expected


@pytest.mark.parametrize("source", [
    request(query={"lang": "xx"}),
    request(query={"lang": "../../etc/passwd"}),
    request(query={"lang": ""}),
    request(cookies={"lang": "not a locale"}),
    request(headers={"Accept-Language": "!!"})
])
def test_unresolvable_request_locale_falls_back(selection, source):
    from webfluid.core.context import FluidContext
    from webfluid.extensions.babel.utils import _request_locale

    with FluidContext(None, source):
        assert str(_request_locale()) == "en"


@pytest.mark.parametrize("source, expected", [
    (request(cookies={"tz": "Europe/Berlin"}), "Europe/Berlin"),
    (request(headers={"X-Timezone": "Europe/Berlin"}), "Europe/Berlin"),
    (request(cookies={"tz": "Mars/Olympus"}), "UTC"),
    (request(cookies={"tz": "../../etc/passwd"}), "UTC"),
    (request(), "UTC"),
    (None, "UTC")
])
def test_request_timezone_falls_back_on_junk(selection, source, expected):
    from webfluid.core.context import FluidContext
    from webfluid.extensions.babel.utils import _request_timezone

    with FluidContext(None, source):
        assert str(_request_timezone()) == expected


def test_to_utc_converts_before_dropping_the_offset(selection):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from webfluid.core.context import FluidContext
    from webfluid.extensions.babel.utils import to_user_timezone, to_utc

    berlin = request(cookies={"tz": "Europe/Berlin"})

    with FluidContext(None, berlin):
        assert to_utc(
            datetime(2026, 8, 3, 12, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        ) == datetime(2026, 8, 3, 10, 0)

    with FluidContext(None, berlin):
        assert to_utc(
            to_user_timezone(datetime(2026, 8, 3, 10, 0))
        ) == datetime(2026, 8, 3, 10, 0)


async def test_afetch_matches_fetch(bound):
    service = TransactionService(LOCALE, DOMAIN)

    assert service._fetch("greeting", 1, None) == "Moin"
    assert await service._afetch("greeting", 1, None) == "Moin"


async def test_afetch_returns_none_for_unknown_keys(bound):
    service = TransactionService(LOCALE, DOMAIN)

    assert await service._afetch("unknown", 1, None) is None
    assert await service._afetch("greeting", 1, "ctx") is None


async def test_aget_reads_the_database_for_uncached_keys(bound):
    service = TransactionService(LOCALE, DOMAIN)

    assert await service.aget("greeting") == service.get("greeting") == "Moin"


async def test_aget_uses_the_memory_cache_for_cached_keys(bound):
    Cache._db_cache = {
        LOCALE: { DOMAIN: { "farewell": { "one": { "": "Tschuess" } } } }
    }
    service = TransactionService(LOCALE, DOMAIN)

    assert await service.aget("farewell") == "Tschuess"


async def test_agettext_prefers_the_database(bound):
    t = MergedTranslations(Catalog({ "greeting": "aus dem Katalog" }), LOCALE, DOMAIN)

    assert await t.agettext("greeting") == t.gettext("greeting") == "Moin"


async def test_agettext_falls_back_to_the_catalog(bound):
    uncached("bye")
    t = MergedTranslations(Catalog({ "bye": "Tschuess" }), LOCALE, DOMAIN)

    assert await t.agettext("bye") == t.gettext("bye") == "Tschuess"


async def test_plural_and_context_variants_fall_back_to_the_catalog(bound):
    uncached("apple")
    t = MergedTranslations(
        Catalog({ "apple": "Apfel", ("fruit", "apple"): "Apfel (Frucht)" }),
        LOCALE, DOMAIN
    )

    assert await t.angettext("apple", "apples", 1) == "Apfel"
    assert await t.apgettext("fruit", "apple") == "Apfel (Frucht)"
    assert await t.anpgettext("fruit", "apple", "apples", 2) == "Apfel (Frucht)"


async def test_async_variants_mirror_their_sync_pendants(bound):
    uncached("apple")
    messages = { "apple": "Apfel", ("fruit", "apple"): "Apfel (Frucht)" }
    t = MergedTranslations(Catalog(messages), LOCALE, DOMAIN)

    assert await t.angettext("apple", "apples", 1) == t.ngettext("apple", "apples", 1)
    assert await t.apgettext("fruit", "apple") == t.pgettext("fruit", "apple")
    assert await t.anpgettext("fruit", "apple", "apples", 2) \
        == t.npgettext("fruit", "apple", "apples", 2)


async def test_startup_load_fills_the_cache_from_the_database(catalog):
    await TransactionService.load(LOCALE, DOMAIN)

    assert Cache._db_cache[LOCALE][DOMAIN] == {
        "greeting": { "one": { "": "Moin", "formal": "Moin Chef" } },
        "apples": { "one": { "": "ein Apfel" }, "other": { "": "viele Aepfel" } }
    }


async def test_startup_load_keeps_locales_and_domains_apart(catalog):
    await TransactionService.load(LOCALE, DOMAIN)
    await TransactionService.load(LOCALE, ADMIN)

    assert "dashboard" not in Cache._db_cache[LOCALE][DOMAIN]
    assert Cache._db_cache[LOCALE][ADMIN] == {
        "dashboard": { "one": { "": "Uebersicht" } }
    }
    assert "en" not in Cache._db_cache


async def test_startup_load_leaves_uncached_keys_to_the_database(catalog):
    await TransactionService.load(LOCALE, DOMAIN)

    assert Cache._uncached[DOMAIN] == { "secret" }
    assert "secret" not in Cache._db_cache[LOCALE][DOMAIN]
    assert await TransactionService(LOCALE, DOMAIN).aget("secret") == "geheim"


async def test_startup_load_runs_once_per_locale_and_domain(catalog):
    await TransactionService.load(LOCALE, DOMAIN)
    Cache._db_cache[LOCALE][DOMAIN]["greeting"] = { "one": { "": "unberuehrt" } }
    await TransactionService.load(LOCALE, DOMAIN)

    assert Cache._db_cache[LOCALE][DOMAIN]["greeting"]["one"][""] == "unberuehrt"


async def test_startup_hook_loads_every_supported_locale(catalog):
    babel = SimpleNamespace(supported_locales=(LOCALE, "en"))
    domains = SimpleNamespace(
        default_domain=SimpleNamespace(domain=DOMAIN),
        store={ ADMIN: SimpleNamespace(domain=ADMIN) }
    )

    await Translations(True).startup_hook(babel, domains)

    assert set(Cache._db_cache) == { LOCALE, "en" }
    assert set(Cache._db_cache[LOCALE]) == { DOMAIN, ADMIN }
    assert Cache._db_cache["en"][DOMAIN] == { "greeting": { "one": { "": "Hi" } } }


async def test_update_writes_the_catalog_and_caches_it(catalog):
    await TransactionService.update(DOMAIN, lambda: {
        LOCALE: { "farewell": { json.dumps({ "pf": "one" }): "Tschuess" } }
    })

    assert Cache._db_cache[LOCALE][DOMAIN]["farewell"]["one"][""] == "Tschuess"
    assert TransactionService(LOCALE, DOMAIN).get("farewell") == "Tschuess"


@pytest.fixture
def isolated_domains(tmp_path):
    bind_database(tmp_path)
    yield
    reset_database()


async def test_kid_keeps_the_same_source_string_isolated_per_domain(isolated_domains):
    await TransactionService.set(LOCALE, DOMAIN, "shared", "geteilt", "one", None)
    await TransactionService.set(LOCALE, ADMIN, "shared", "geteilt (admin)", "one", None)

    Cache._db_cache = {}
    await TransactionService.load(LOCALE, DOMAIN)
    await TransactionService.load(LOCALE, ADMIN)

    assert Cache._db_cache[LOCALE][DOMAIN]["shared"]["one"][""] == "geteilt"
    assert Cache._db_cache[LOCALE][ADMIN]["shared"]["one"][""] == "geteilt (admin)"


async def test_resolve_keys_keeps_the_same_source_string_isolated_per_domain(isolated_domains):
    await TransactionService.update(DOMAIN, lambda: {
        LOCALE: { "shared": { json.dumps({ "pf": "one" }): "geteilt" } }
    })
    await TransactionService.update(ADMIN, lambda: {
        LOCALE: { "shared": { json.dumps({ "pf": "one" }): "geteilt (admin)" } }
    })

    Cache._db_cache = {}
    await TransactionService.load(LOCALE, DOMAIN)
    await TransactionService.load(LOCALE, ADMIN)

    assert Cache._db_cache[LOCALE][DOMAIN]["shared"]["one"][""] == "geteilt"
    assert Cache._db_cache[LOCALE][ADMIN]["shared"]["one"][""] == "geteilt (admin)"


async def test_uncache_and_recache_round_trip(catalog):
    await TransactionService.load(LOCALE, DOMAIN)
    service = TransactionService(LOCALE, DOMAIN)

    await service.uncache("greeting")
    assert "greeting" not in Cache._db_cache[LOCALE][DOMAIN]
    assert await service.aget("greeting") == "Moin"

    await service.recache("greeting")
    assert Cache._db_cache[LOCALE][DOMAIN]["greeting"]["one"][""] == "Moin"
    assert "greeting" not in Cache._uncached[DOMAIN]


@pytest.fixture
def translator(bound, monkeypatch):
    domains = [
        Domain(MergedTranslations(Catalog(), LOCALE, DOMAIN)),
        Domain(MergedTranslations(
            Catalog({ "welcome": "Willkommen", "hello": "Hallo %(name)s" }),
            LOCALE, DOMAIN
        ))
    ]
    monkeypatch.setattr(
        Translator, "_fallback_escalation", property(lambda self: domains)
    )

    return Translator(None, True)


async def test_agettext_escalates_through_the_domains(translator):
    uncached("welcome")

    assert await translator.agettext("welcome") == "Willkommen"
    assert translator.gettext("welcome") == "Willkommen"


async def test_agettext_returns_the_key_when_no_domain_matches(translator):
    uncached("missing")

    assert await translator.agettext("missing") == "missing"


async def test_agettext_interpolates_variables(translator):
    uncached("hello")

    assert await translator.agettext(
        "hello", name="Pierre"
    ) == "Hallo Pierre"


async def test_apgettext_falls_back_to_agettext(translator):
    uncached("welcome")

    assert await translator.apgettext("nowhere", "welcome") == "Willkommen"


@pytest.fixture
def identity_translator(bound, monkeypatch):
    domains = [
        Domain(MergedTranslations(Catalog({ "Save": "Save" }), LOCALE, DOMAIN)),
        Domain(MergedTranslations(
            Catalog({ "Save": "Speichern", "Open": "Oeffnen" }), LOCALE, DOMAIN
        ))
    ]
    monkeypatch.setattr(
        Translator, "_fallback_escalation", property(lambda self: domains)
    )

    return Translator(None, True)


async def test_a_translation_equal_to_its_source_wins_its_domain(identity_translator):
    uncached("Save")

    assert identity_translator.gettext("Save") == "Save"
    assert await identity_translator.agettext("Save") == "Save"


async def test_a_real_miss_still_escalates(identity_translator):
    uncached("Open")

    assert identity_translator.gettext("Open") == "Oeffnen"
    assert await identity_translator.agettext("Open") == "Oeffnen"


@pytest.fixture
def compiled(tmp_path):
    from babel.messages.catalog import Catalog as MessageCatalog
    from babel.messages.mofile import write_mo
    from babel.support import Translations as BabelTranslations

    messages = tmp_path / LOCALE / "LC_MESSAGES"
    messages.mkdir(parents=True)

    catalog = MessageCatalog(locale=LOCALE)
    catalog.add("Save", "Save")
    catalog.add("bank", "Ufer", context="river")
    catalog.add(("apple", "apples"), ("Apfel", "Aepfel"))
    with open(messages / f"{DOMAIN}.mo", "wb") as f: write_mo(f, catalog)

    return BabelTranslations.load(tmp_path, [LOCALE], domain=DOMAIN)


def test_the_catalog_probe_matches_every_key_shape(bound, compiled):
    t = MergedTranslations(compiled, LOCALE, DOMAIN)
    uncached("Save", "bank", "apple", "nothing")

    assert t.findtext("Save") == "Save"
    assert t.pfindtext("river", "bank") == "Ufer"
    assert t.nfindtext("apple", "apples", 2) == "Aepfel"

    assert t.findtext("nothing") is None
    assert t.pfindtext("river", "nothing") is None
    assert t.nfindtext("nothing", "nothings", 2) is None


def test_gettext_still_answers_with_the_source_on_a_miss(bound, compiled):
    t = MergedTranslations(compiled, LOCALE, DOMAIN)
    uncached("nothing")

    assert t.gettext("nothing") == "nothing"
    assert t.ngettext("nothing", "nothings", 2) == "nothings"
