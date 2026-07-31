import os, pytest

os.environ.setdefault("EXT_SQLALCHEMY", "1")

from webfluid.core.config.default import DefaultConfig
from webfluid.core.ext import db
from webfluid.core.identity import FRAMEWORK_ID, FRAMEWORK_NAME
from webfluid.extensions.babel.translations import (
    Cache, I18nKey, I18nMessage, TransactionService
)
from webfluid.extensions.sqlalchemy.sqlalchemy import SQLAlchemy

LOCALE = "en"

_FLAGS = (
    ("webfluid.core.fluid.extensions", "EXT_SQLALCHEMY"),
    ("webfluid.core.fluid.extensions", "EXT_BABEL"),
    ("webfluid.core.fluid.extensions", "EXECUTION"),
    ("webfluid.extensions.babel.babel.main", "EXT_SQLALCHEMY")
)


@pytest.fixture
def mixed(make_fluid, tmp_path, monkeypatch):
    monkeypatch.setattr(
        DefaultConfig, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{tmp_path / 'app.db'}"
    )
    for module, flag in _FLAGS: monkeypatch.setattr(f"{module}.{flag}", True)

    Cache._db_cache = {}
    Cache._uncached = {}
    TransactionService._locks = {}

    fluid = make_fluid()
    db.Model.metadata.create_all(db.get_bind("default").sync_engine)

    yield fluid

    db._binds.clear()
    SQLAlchemy._instance = None
    Cache._db_cache = {}
    Cache._uncached = {}
    TransactionService._locks = {}


async def test_startup_loads_the_framework_translations(mixed):
    await mixed._lifecycle.run_startup()

    domain = Cache._db_cache[LOCALE][FRAMEWORK_ID]
    assert domain["BRAND"]["one"][""] == FRAMEWORK_NAME
    assert domain["MIN_LENGTH"]["other"][""].startswith("Password must be at least")


async def test_startup_persists_the_framework_translations(mixed):
    from sqlalchemy import select
    from webfluid.fluid.i18n import translations

    catalog = translations()
    expected_keys = { key for entries in catalog.values() for key in entries }
    expected_messages = sum(
        len(forms) for entries in catalog.values() for forms in entries.values()
    )

    await mixed._lifecycle.run_startup()

    with db.executor(model=I18nKey) as e:
        keys = { row.key for row in e.exec(
            select(I18nKey).where(I18nKey.domain == FRAMEWORK_ID)
        ).all() }
        messages = len(e.exec(select(I18nMessage)).all())

    assert keys == expected_keys
    assert messages == expected_messages


async def test_startup_seals_the_phase_and_prepares_the_app(mixed):
    await mixed._lifecycle.run_startup()

    assert mixed._sources.frozen
    assert mixed.static_prefixes.frozen
    with pytest.raises(RuntimeError): mixed.startup_hook(lambda: None)


async def test_i18n_socket_is_mounted(mixed):
    assert any(
        getattr(route, "path", None) == "/ws/i18n" for route in mixed.routes
    )


async def test_translation_updates_are_blocked_after_startup(mixed):
    from webfluid.exceptions import FrameworkException
    from webfluid.core.ext import babel

    await mixed._lifecycle.run_startup()

    with pytest.raises(FrameworkException):
        babel.update_translations(FRAMEWORK_ID, lambda: {})


async def test_a_failing_startup_hook_does_not_stop_the_bootstrap(mixed, monkeypatch):
    logged = []
    monkeypatch.setattr(
        "webfluid.utils.logging.factory.exception",
        lambda exc, message=None: logged.append(exc)
    )
    reached = []

    mixed.startup_hook(lambda: (_ for _ in ()).throw(RuntimeError("kaputt")))
    mixed.startup_hook(lambda: reached.append(True))

    await mixed._lifecycle.run_startup()

    assert reached == [True]
    assert [type(exc) for exc in logged] == [RuntimeError]


async def test_shutdown_runs_after_startup(mixed):
    stopped = []
    mixed.shutdown_hook(lambda: stopped.append(True))

    await mixed._lifecycle.run_startup()
    await mixed._lifecycle.run_shutdown()

    assert stopped == [True]
