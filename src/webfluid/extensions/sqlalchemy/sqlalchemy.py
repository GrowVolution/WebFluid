from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING, Optional, Generator, AsyncGenerator

from webfluid.extensions.base import FluidExtension
from webfluid.extensions.sqlalchemy.utils import (
    Model, Bind, Executor, AsyncExecutor, database_uris
)
from webfluid.exceptions import FrameworkException

if TYPE_CHECKING:
    from webfluid import Fluid


class SQLAlchemy(FluidExtension):
    _instance = None

    def __init__(self,
                 fluid: Optional["Fluid"] = None,
                 base: type[DeclarativeBase] = Model):
        if SQLAlchemy._instance is not None:
            raise FrameworkException("SQLAlchemy.expand_fluid() has already been called!")

        self.Model = base
        self._binds = {}

        super().__init__(fluid)

    def expand_fluid(self, fluid: "Fluid", *_, **__):
        default_uri = fluid.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///app.db")
        uris = database_uris(default_uri)
        self._binds["default"] = Bind("default", uris)

        further_binds = fluid.config.get("SQLALCHEMY_BINDS", {})
        for key, uri in further_binds.items():
            uris = database_uris(uri)
            self._binds[key] = Bind(key, uris)

        SQLAlchemy._instance = self

    def _resolve_bind(self, bind_key: Optional[str], model: Optional[type]) -> Bind:
        if not (bind_key or model): bind = self._binds["default"]
        elif bind_key: bind = self.get_bind(bind_key)
        else: bind = self.get_bind_for_model(model)
        return bind

    def get_bind(self, bind_key: str) -> Bind:
        bind: Optional[Bind] = self._binds.get(bind_key)
        if not bind: raise KeyError(
            f"Unknown bind key: '{bind_key}'"
        )
        return bind

    def get_bind_for_model(self, model: Optional[type]) -> Bind:
        return self.get_bind(getattr(model, "__bind_key__", "default"))

    @contextmanager
    def executor(
            self, bind_key: Optional[str] = None,
            model: Optional[type] = None
    ) -> Generator[Executor, None, None]:
        with self._resolve_bind(bind_key, model).session() as session:
            with Executor(session) as e: yield e

    @asynccontextmanager
    async def async_executor(
            self, bind_key: Optional[str] = None,
            model: Optional[type] = None
    ) -> AsyncGenerator[AsyncExecutor, None]:
        async with self._resolve_bind(bind_key, model).async_session() as session:
            async with AsyncExecutor(session) as e: yield e

    @contextmanager
    def outer_executor(self, depth: int = 1) -> Generator[Executor, None, None]:
        with Executor.outer(depth) as e:
            if not e: raise FrameworkException(
                f"No outer executor found at depth {depth}!"
            )
            yield e

    @contextmanager
    def outer_async_executor(
            self, depth: int = 1
    ) -> Generator[AsyncExecutor, None, None]:
        with AsyncExecutor.outer(depth) as e:
            if not e: raise FrameworkException(
                f"No outer async executor found at depth {depth}!"
            )
            yield e

    @property
    def current_executor(self) -> Executor:
        return Executor.current()

    @property
    def current_async_executor(self) -> AsyncExecutor:
        return AsyncExecutor.current()

    @property
    def bind_keys(self) -> list[str]:
        return list(self._binds.keys())

    @classmethod
    def get_instance(cls) -> "SQLAlchemy":
        if cls._instance is None:
            raise FrameworkException("SQLAlchemy.expand_fluid() was never called!")
        return cls._instance
