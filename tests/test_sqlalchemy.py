from sqlalchemy import select
import os, pytest

os.environ.setdefault("EXT_SQLALCHEMY", "1")

from webfluid.core.ext import db
from webfluid.exceptions import FrameworkException
from webfluid.extensions.babel.translations import I18nKey
from webfluid.extensions.sqlalchemy.bind import Bind
from webfluid.extensions.sqlalchemy.executor import AsyncExecutor, Executor
from webfluid.extensions.sqlalchemy.sqlalchemy import SQLAlchemy


@pytest.fixture
def bound(tmp_path):
    path = tmp_path / "app.db"
    bind = Bind("default", (f"sqlite:///{path}", f"sqlite+aiosqlite:///{path}"))

    db._binds["default"] = bind
    SQLAlchemy._instance = db
    db.Model.metadata.create_all(bind.sync_engine)

    yield bind

    db._binds.clear()
    SQLAlchemy._instance = None


def test_rows_stay_readable_after_the_executor_closes(bound):
    with db.executor(model=I18nKey) as e:
        e.insert(I18nKey("greeting", "messages"), flush=True)

    with db.executor(model=I18nKey) as e:
        row = e.exec(select(I18nKey)).first()

    assert (row.key, row.domain, row.cached) == ("greeting", "messages", True)


async def test_async_rows_stay_readable_after_the_executor_closes(bound):
    async with db.async_executor(model=I18nKey) as e:
        await e.insert(I18nKey("farewell", "messages"), flush=True)

    async with db.async_executor(model=I18nKey) as e:
        result = await e.exec(select(I18nKey))
        row = result.first()

    assert (row.key, row.domain, row.cached) == ("farewell", "messages", True)


def test_deleting_through_the_executor(bound):
    with db.executor(model=I18nKey) as e:
        e.insert(I18nKey("gone", "messages"), flush=True)

    with db.executor(model=I18nKey) as e:
        e.delete(e.exec(select(I18nKey)).first(), flush=True)
        assert e.exec(select(I18nKey)).all() == []


async def test_async_deleting_through_the_executor(bound):
    async with db.async_executor(model=I18nKey) as e:
        await e.insert(I18nKey("gone", "messages"), flush=True)

    async with db.async_executor(model=I18nKey) as e:
        result = await e.exec(select(I18nKey))
        await e.delete(result.first(), flush=True)

        assert (await e.exec(select(I18nKey))).all() == []


def test_a_failing_executor_rolls_back(bound):
    with pytest.raises(RuntimeError):
        with db.executor(model=I18nKey) as e:
            e.insert(I18nKey("rolled-back", "messages"), flush=True)
            raise RuntimeError("kaputt")

    with db.executor(model=I18nKey) as e:
        assert e.exec(select(I18nKey)).all() == []


async def test_a_failing_async_executor_rolls_back(bound):
    with pytest.raises(RuntimeError):
        async with db.async_executor(model=I18nKey) as e:
            await e.insert(I18nKey("rolled-back", "messages"), flush=True)
            raise RuntimeError("kaputt")

    async with db.async_executor(model=I18nKey) as e:
        assert (await e.exec(select(I18nKey))).all() == []


def test_the_ensured_executor_joins_an_open_one(bound):
    with db.executor(model=I18nKey) as outer:
        with db.ensured_executor(model=I18nKey) as e:
            assert e is outer

    with db.ensured_executor(model=I18nKey) as e:
        assert isinstance(e, Executor)
        assert Executor.try_current() is e

    assert Executor.try_current() is None


async def test_the_ensured_async_executor_joins_an_open_one(bound):
    async with db.async_executor(model=I18nKey) as outer:
        async with db.ensured_async_executor(model=I18nKey) as e:
            assert e is outer

    async with db.ensured_async_executor(model=I18nKey) as e:
        assert isinstance(e, AsyncExecutor)
        assert AsyncExecutor.try_current() is e

    assert AsyncExecutor.try_current() is None


def test_binds_are_resolved_by_key_and_by_model(bound):
    assert db.bind_keys == ["default"]
    assert db.get_bind("default") is bound
    assert db.get_bind_for_model(I18nKey) is bound

    with pytest.raises(KeyError): db.get_bind("missing")


def test_an_unexpanded_extension_refuses_to_resolve():
    db._binds.clear()
    SQLAlchemy._instance = None

    with pytest.raises(FrameworkException): db.bind_keys
    with pytest.raises(FrameworkException): SQLAlchemy.get_instance()
