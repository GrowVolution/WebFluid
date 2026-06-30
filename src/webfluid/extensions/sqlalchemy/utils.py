from sqlalchemy import MetaData, create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker, declared_attr
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from contextvars import ContextVar
from contextlib import asynccontextmanager, contextmanager

from webfluid.core.context import BaseContext
from webfluid.utils.core import async_result, camel_to_snake
from webfluid.exceptions import FrameworkException


class Model(DeclarativeBase):
    __bind_set__ = False
    __metadata__ = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        key = cls.__dict__.get("__bind_key__")
        if key and not cls.__bind_set__:
            cls.set_bind(key)

    def __hash__(self):
        state = inspect(self)
        return hash(state.identity)

    @declared_attr
    def __tablename__(cls):
        tablename = cls.__dict__.get("__tablename__")
        if isinstance(tablename, str):
            return tablename
        return camel_to_snake(cls.__name__)

    @classmethod
    def metadata_for(cls, key):
        if key == "default": return Model.metadata
        md = Model.__metadata__.get(key)
        if md is None:
            md = MetaData()
            Model.__metadata__[key] = md
        return md

    @classmethod
    def set_bind(cls, key):
        if cls.__bind_set__:
            raise FrameworkException(
                f"DB bind has already been set for {cls.__name__}!"
            )
        cls.__bind_key__ = key
        cls.__bind_set__ = True

        table = getattr(cls, "__table__", None)
        target = cls.metadata_for(key)
        if table is None or table.metadata is target: return

        update_metadata(table, target)


class Bind:
    def __init__(self, key, uris, metadata=None):

        sync_uri, async_uri = uris

        self.name = key
        self.metadata = metadata if metadata else Model.metadata_for(key)
        self.sync_engine = create_engine(sync_uri)
        self.async_engine = create_async_engine(async_uri)
        self._sync_session = sessionmaker(self.sync_engine)
        self._async_session = async_sessionmaker(self.async_engine)

    @contextmanager
    def session(self):
        with self._sync_session() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

    @asynccontextmanager
    async def async_session(self):
        async with self._async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


class Executor(BaseContext):
    _ctx = ContextVar("sqlalchemy.executor")
    def __init__(self, session):
        self.session = session

    def exec(self, statement, scalars=True):
        results = self.session.execute(statement)
        if scalars: return results.scalars()
        return results

    def insert(self, obj, flush=False):
        self.session.add(obj)
        if flush: self.flush()
        return obj

    def delete(self, obj, flush=False):
        self.session.delete(obj)
        if flush: self.flush()

    def flush(self):
        self.session.flush()


class AsyncExecutor(BaseContext):
    _ctx = ContextVar("sqlalchemy.async_executor")
    def __init__(self, session):
        self.session = session

    async def exec(self, statement, scalars=True):
        results = await self.session.execute(statement)
        if scalars: return results.scalars()
        return results

    async def insert(self, obj, flush=False):
        self.session.add(obj)
        if flush: await self.flush()
        return obj

    async def delete(self, obj, flush=False):
        await async_result(self.session.delete(obj))
        if flush: await self.flush()

    async def flush(self):
        await self.session.flush()


def database_uris(uri):
    if "+" in uri.split("://")[0]:
        raise ValueError(f"Invalid database URI '{uri}': Please do not define drivers.")

    if uri.startswith("sqlite:"):
        sync_uri = uri
        async_uri = uri.replace("sqlite", "sqlite+aiosqlite")
    elif uri.startswith("postgresql:"):
        sync_uri = uri.replace("postgresql", "postgresql+psycopg")
        async_uri = sync_uri
    elif uri.startswith("mysql:"):
        sync_uri = uri.replace("mysql", "mysql+pymysql")
        async_uri = uri.replace("mysql", "mysql+aiomysql")
    else:
        raise ValueError(f"Invalid database URI '{uri}': Unsupported database type.")

    return sync_uri, async_uri


def update_metadata(table, target_md=None, target_bind=None, target_model=None):
    if target_md: md = target_md

    elif target_bind:
        from .sqlalchemy import SQLAlchemy
        db = SQLAlchemy.get_instance()
        bind = db.get_bind(target_bind)
        md = bind.metadata

    elif target_model:
        if not issubclass(target_model, DeclarativeBase):
            raise ValueError(f"Invalid model type '{target_model}'.")
        md = getattr(target_model.__table__, "metadata", target_model.metadata)

    else: raise ValueError("Failed to resolve metadata.")

    table.metadata._remove_table(table.name, table.schema)
    table.metadata = md
    md._add_table(table.name, table.schema, table)
