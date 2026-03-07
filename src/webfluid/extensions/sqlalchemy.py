from sqlalchemy import ScalarResult, Result, Select, create_engine
from sqlalchemy.orm import Session, DeclarativeBase, sessionmaker, declared_attr
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Optional, Any

from webfluid.core.context import BaseContext
from webfluid.utils import camel_to_snake
from webfluid.extensions.utils.sqlalchemy import database_uris

if TYPE_CHECKING:
    from webfluid import Fluid


class _Executor(BaseContext):
    ctx = ContextVar("sqlalchemy.executor")
    def __init__(self, session: Session | AsyncSession):
        self.session = session

    def exec(self, statement: Select[Any],
             scalars: bool = True) -> ScalarResult | Result:
        results = self.session.execute(statement)
        if scalars: return results.scalars()
        return results

    async def exec_async(self, statement: Select[Any],
                         scalars: bool = True) -> ScalarResult | Result:
        results = await self.session.execute(statement)
        if scalars: return results.scalars()
        return results


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
            except:
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
            except:
                await session.rollback()
                raise
            finally:
                await session.close()


class Model(DeclarativeBase):
    __tablename__: Optional[str]
    __bind_key__: Optional[str]

    @classmethod
    @declared_attr.directive
    def __tablename__(cls) -> str:
        if "__tablename__" in cls.__dict__:
            return cls.__dict__["__tablename__"]
        return camel_to_snake(cls.__name__)


class SQLAlchemy:
    def __init__(self,
                 fluid: "Fluid | None" = None,
                 base: type[DeclarativeBase] = Model):
        self.Model = base
        self.binds = {}

        if fluid is not None: self.init_fluid(fluid)

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

    def init_fluid(self, fluid: "Fluid"):
        default_uri = fluid.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///app.db")
        uris = database_uris(default_uri)
        fluid.config["SQLALCHEMY_DATABASE_URI"] = uris[0]
        self.binds["default"] = _Bind("default", uris)

        further_binds = fluid.config.get("SQLALCHEMY_BINDS", {})
        for key, uri in further_binds.items():
            uris = database_uris(uri)
            fluid.config["SQLALCHEMY_BINDS"][key] = uris[0]
            self.binds[key] = _Bind(key, uris)

    @contextmanager
    def executor(self, bind_key: str = None, model: type[Model] = None):
        with self._resolve_bind(bind_key, model).session() as session:
            with _Executor(session) as e: yield e

    @asynccontextmanager
    async def async_executor(self, bind_key: str = None, model: type[Model] = None):
        async with self._resolve_bind(bind_key, model).async_session() as session:
            async with _Executor(session) as e: yield e
