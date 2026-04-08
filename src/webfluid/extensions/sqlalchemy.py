from sqlalchemy import ScalarResult, Result, Select, create_engine
from sqlalchemy.orm import Session, DeclarativeBase, sessionmaker, declared_attr
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Optional

from webfluid.extensions.base import FluidExtension
from webfluid.core.context import BaseContext
from webfluid.utils.framework import camel_to_snake
from webfluid.extensions.utils.sqlalchemy import database_uris
from webfluid.exceptions import FrameworkException

if TYPE_CHECKING:
    from webfluid.core.fluid import Fluid


class _Executor(BaseContext):
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


class _AsyncExecutor(BaseContext):
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
        await self.session.delete(obj)
        if flush: await self.flush()

    async def flush(self):
        await self.session.flush()


class _Bind:
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


class SQLAlchemy(FluidExtension):
    # TODO: Add optional Multi-Metadata later
    _instance = None

    def __init__(self,
                 fluid: "Fluid | None" = None,
                 base: type[DeclarativeBase] = Model):
        if SQLAlchemy._instance is not None:
            raise FrameworkException("SQLAlchemy.expand_fluid() has already been called!")

        self.Model = base
        self.binds = {}

        super().__init__(fluid)

    def expand_fluid(self, fluid: "Fluid", *_, **__):
        default_uri = fluid.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///app.db")
        uris = database_uris(default_uri)
        fluid.config["SQLALCHEMY_DATABASE_URI"] = uris[0]
        self.binds["default"] = _Bind("default", uris)

        further_binds = fluid.config.get("SQLALCHEMY_BINDS", {})
        for key, uri in further_binds.items():
            uris = database_uris(uri)
            fluid.config["SQLALCHEMY_BINDS"][key] = uris[0]
            self.binds[key] = _Bind(key, uris)

        SQLAlchemy._instance = self

    def _get_bind(self, bind_key: str) -> _Bind:
        try: return self.binds[bind_key]
        except KeyError: raise RuntimeError("Failed to resolve sqlalchemy bind.")

    def _resolve_bind(self, bind_key: str, model: type[Model]) -> _Bind:
        if not (bind_key or model): bind = self.binds["default"]
        elif bind_key: bind = self._get_bind(bind_key)
        else: bind = self.get_bind_for_model(model)
        return bind

    def get_bind_for_model(self, model: type[Model]) -> _Bind:
        return self._get_bind(getattr(model, "__bind_key__", "default"))

    @contextmanager
    def executor(self, bind_key: str = None, model: type[Model] = None):
        with self._resolve_bind(bind_key, model).session() as session:
            with _Executor(session) as e: yield e

    @asynccontextmanager
    async def async_executor(self, bind_key: str = None, model: type[Model] = None):
        async with self._resolve_bind(bind_key, model).async_session() as session:
            async with _AsyncExecutor(session) as e: yield e

    @classmethod
    def get_instance(cls) -> "SQLAlchemy":
        if cls._instance is None:
            raise FrameworkException("SQLAlchemy.expand_fluid() was never called!")
        return cls._instance
