from sqlalchemy import ScalarResult, Result, MetaData, Table, create_engine, inspect
from sqlalchemy.orm import Session, DeclarativeBase, sessionmaker, declared_attr
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from contextvars import ContextVar
from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING, Optional, Any

from webfluid.core.context import BaseContext
from webfluid.utils.framework import async_result, camel_to_snake
from webfluid.exceptions import FrameworkException

if TYPE_CHECKING:
    from sqlalchemy.sql.expression import Insert, Select, Update, Delete


class Model(DeclarativeBase):
    __tablename__: Optional[str]
    __bind_key__: Optional[str]
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
    def __tablename__(cls) -> str:
        tablename = cls.__dict__.get("__tablename__")
        if isinstance(tablename, str):
            return tablename
        return camel_to_snake(cls.__name__)

    @classmethod
    def metadata_for(cls, key: str) -> MetaData:
        if key == "default": return Model.metadata
        md = Model.__metadata__.get(key)
        if md is None:
            md = MetaData()
            Model.__metadata__[key] = md
        return md

    @classmethod
    def set_bind(cls, key: str):
        if cls.__bind_set__:
            raise FrameworkException(
                f"DB bind has already been set for {cls.__name__}!"
            )
        cls.__bind_key__ = key
        cls.__bind_set__ = True

        table: Optional[Table] = getattr(cls, "__table__", None)
        target = cls.metadata_for(key)
        if table is None or table.metadata is target: return

        update_metadata(table, target)


class Bind:
    def __init__(self, key: str, uris: tuple[str, str],
                 metadata: Optional[MetaData] = None):

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
    def __init__(self, session: Session):
        self.session = session

    def exec(self, statement: "Insert | Select | Update | Delete",
             scalars: bool = True) -> ScalarResult | Result:
        results = self.session.execute(statement)
        if scalars: return results.scalars()
        return results

    def insert(self, obj: Any, flush: bool = False) -> Any:
        self.session.add(obj)
        if flush: self.flush()
        return obj

    def delete(self, obj: Any, flush: bool = False):
        self.session.delete(obj)
        if flush: self.flush()

    def flush(self):
        self.session.flush()


class AsyncExecutor(BaseContext):
    _ctx = ContextVar("sqlalchemy.async_executor")
    def __init__(self, session: AsyncSession):
        self.session = session

    async def exec(self, statement: "Insert | Select | Update | Delete",
                   scalars: bool = True) -> ScalarResult | Result:
        results = await self.session.execute(statement)
        if scalars: return results.scalars()
        return results

    async def insert(self, obj: Any, flush: bool = False) -> Any:
        self.session.add(obj)
        if flush: await self.flush()
        return obj

    async def delete(self, obj: Any, flush: bool = False):
        await async_result(self.session.delete(obj))
        if flush: await self.flush()

    async def flush(self):
        await self.session.flush()


def database_uris(uri: str) -> tuple[str, str]:
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


def update_metadata(
        table: Table, target_md: Optional[MetaData] = None,
        target_bind: Optional[str] = None,
        target_model: Optional[type] = None
):
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
