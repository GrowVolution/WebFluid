from sqlalchemy import ScalarResult, Result, Select, create_engine
from sqlalchemy.orm import Session, DeclarativeBase, sessionmaker, declared_attr
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from contextvars import ContextVar
from contextlib import asynccontextmanager, contextmanager
from typing import Optional

from webfluid.core.context import BaseContext
from webfluid.utils.framework import async_result, camel_to_snake
from webfluid.exceptions import FrameworkException


class Model(DeclarativeBase):
    __tablename__: Optional[str]
    __bind_key__: Optional[str]
    __bind_set__ = False

    @declared_attr
    def __tablename__(cls) -> str:
        tablename = cls.__dict__.get("__tablename__")
        if isinstance(tablename, str):
            return tablename
        return camel_to_snake(cls.__name__)

    @classmethod
    def set_bind(cls, key: str):
        if cls.__bind_set__:
            raise FrameworkException(
                f"DB bind has already been set for {cls.__name__}!"
            )
        cls.__bind_key__ = key
        cls.__bind_set__ = True


class Bind:
    def __init__(self, key: str, uris: tuple[str, str]):
        sync_uri, async_uri = uris

        self.name = key
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

    def exec(self, statement: Select,
             scalars: bool = True) -> ScalarResult | Result:
        results = self.session.execute(statement)
        if scalars: return results.scalars()
        return results

    def insert(self, obj: Model, flush: bool = False) -> Model:
        self.session.add(obj)
        if flush: self.flush()
        return obj

    def delete(self, obj: Model, flush: bool = False):
        self.session.delete(obj)
        if flush: self.flush()

    def flush(self):
        self.session.flush()


class AsyncExecutor(BaseContext):
    _ctx = ContextVar("sqlalchemy.async_executor")
    def __init__(self, session: AsyncSession):
        self.session = session

    async def exec(self, statement: Select,
                   scalars: bool = True) -> ScalarResult | Result:
        results = await self.session.execute(statement)
        if scalars: return results.scalars()
        return results

    async def insert(self, obj: Model, flush: bool = False) -> Model:
        self.session.add(obj)
        if flush: await self.flush()
        return obj

    async def delete(self, obj: Model, flush: bool = False):
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
