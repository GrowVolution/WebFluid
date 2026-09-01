from contextlib import asynccontextmanager, contextmanager

from webfluid.extensions.sqlalchemy.bind import Bind
from webfluid.extensions.sqlalchemy.model import Model
from webfluid.extensions.sqlalchemy.executor import Executor, AsyncExecutor
from webfluid.extensions.sqlalchemy.utils import database_uris
from webfluid.extensions.base import FluidExtension
from webfluid.exceptions import FrameworkException


class SQLAlchemy(FluidExtension):
    _instance = None

    def __init__(self, fluid=None, base=Model):
        if SQLAlchemy._instance is not None:
            raise FrameworkException("SQLAlchemy.expand_fluid() has already been called.")

        self.Model = base
        self._binds = {}

        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        engine_kwargs = fluid.config["SQLALCHEMY_ENGINE_OPTIONS"]

        self._binds["default"] = Bind(
            "default", database_uris(fluid.config["SQLALCHEMY_DATABASE_URI"]),
            metadata=None, **engine_kwargs
        )

        for key, uri in fluid.config["SQLALCHEMY_BINDS"].items():
            self._binds[key] = Bind(
                key, database_uris(uri), metadata=None, **engine_kwargs
            )

        SQLAlchemy._instance = self
        fluid.shutdown_hook(self.dispose)

    async def dispose(self):
        for bind in self._binds.values(): await bind.dispose()

    def _ensure_initialized(self):
        if not self._binds:
            raise FrameworkException("SQLAlchemy.expand_fluid() has not been called.")

    def _resolve_bind(self, bind_key, model):
        self._ensure_initialized()
        if not (bind_key or model): bind = self._binds["default"]
        elif bind_key: bind = self.get_bind(bind_key)
        else: bind = self.get_bind_for_model(model)
        return bind

    def get_bind(self, bind_key):
        self._ensure_initialized()
        bind = self._binds.get(bind_key)
        if not bind: raise KeyError(
            f"Unknown bind key: '{bind_key}'"
        )
        return bind

    def get_bind_for_model(self, model):
        return self.get_bind(getattr(model, "__bind_key__", "default"))

    @contextmanager
    def executor(self, bind_key=None, model=None):
        with self._resolve_bind(bind_key, model).session() as session:
            with Executor(session) as e: yield e

    @asynccontextmanager
    async def async_executor(self, bind_key=None, model=None):
        async with self._resolve_bind(bind_key, model).async_session() as session:
            with AsyncExecutor(session) as e: yield e

    @contextmanager
    def ensured_executor(self, bind_key=None, model=None):
        e = Executor.try_current()
        if e is not None:
            yield e
            return

        with self.executor(bind_key, model) as e:
            yield e

    @asynccontextmanager
    async def ensured_async_executor(self, bind_key=None, model=None):
        e = AsyncExecutor.try_current()
        if e is not None:
            yield e
            return

        async with self.async_executor(bind_key, model) as e:
            yield e

    @property
    def current_executor(self):
        return Executor.current()

    @property
    def current_async_executor(self):
        return AsyncExecutor.current()

    @property
    def bind_keys(self):
        self._ensure_initialized()
        return list(self._binds.keys())

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            raise FrameworkException("SQLAlchemy.expand_fluid() has never been called.")
        return cls._instance
