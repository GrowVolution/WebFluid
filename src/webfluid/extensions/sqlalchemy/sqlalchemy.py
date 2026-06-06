from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager, contextmanager

from typing import TYPE_CHECKING, Optional

from webfluid.extensions.base import FluidExtension
from webfluid.extensions.sqlalchemy.utils import (
    Model, Bind, Executor, AsyncExecutor, database_uris
)
from webfluid.exceptions import FrameworkException

if TYPE_CHECKING:
    from webfluid.core.fluid import Fluid


class SQLAlchemy(FluidExtension):
    # TODO: Add optional Multi-Metadata later
    _instance = None

    def __init__(self,
                 fluid: Optional["Fluid"] = None,
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
        self.binds["default"] = Bind("default", uris)

        further_binds = fluid.config.get("SQLALCHEMY_BINDS", {})
        for key, uri in further_binds.items():
            uris = database_uris(uri)
            fluid.config["SQLALCHEMY_BINDS"][key] = uris[0]
            self.binds[key] = Bind(key, uris)

        SQLAlchemy._instance = self

    def _get_bind(self, bind_key: str) -> Bind:
        try: return self.binds[bind_key]
        except KeyError: raise RuntimeError("Failed to resolve sqlalchemy bind.")

    def _resolve_bind(self, bind_key: Optional[str], model: Optional[type]) -> Bind:
        if not (bind_key or model): bind = self.binds["default"]
        elif bind_key: bind = self._get_bind(bind_key)
        else: bind = self.get_bind_for_model(model)
        return bind

    def get_bind_for_model(self, model: Optional[type]) -> Bind:
        return self._get_bind(getattr(model, "__bind_key__", "default"))

    @contextmanager
    def executor(self, bind_key: Optional[str] = None, model: Optional[type] = None):
        with self._resolve_bind(bind_key, model).session() as session:
            with Executor(session) as e: yield e

    @asynccontextmanager
    async def async_executor(self, bind_key: Optional[str] = None, model: Optional[type] = None):
        async with self._resolve_bind(bind_key, model).async_session() as session:
            async with AsyncExecutor(session) as e: yield e

    @property
    def current_executor(self) -> Executor:
        return Executor.current()

    @property
    def current_async_executor(self) -> AsyncExecutor:
        return AsyncExecutor.current()

    @classmethod
    def get_instance(cls) -> "SQLAlchemy":
        if cls._instance is None:
            raise FrameworkException("SQLAlchemy.expand_fluid() was never called!")
        return cls._instance
