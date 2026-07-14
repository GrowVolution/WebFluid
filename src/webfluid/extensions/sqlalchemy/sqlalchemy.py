from contextlib import asynccontextmanager, contextmanager

from webfluid.extensions.base import FluidExtension
from webfluid.extensions.sqlalchemy.utils import (
    Model, Bind, Executor, AsyncExecutor, database_uris
)
from webfluid.exceptions import FrameworkException


class SQLAlchemy(FluidExtension):
    _instance = None

    def __init__(self, fluid=None, base=Model):
        if SQLAlchemy._instance is not None:
            raise FrameworkException("SQLAlchemy.expand_fluid() has already been called!")

        self.Model = base
        self._binds = {}

        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        default_uri = fluid.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///app.db")
        engine_kwargs = fluid.config.get("SQLALCHEMY_ENGINE_OPTIONS", {
            "pool_pre_ping": True,
            "pool_recycle": 3600
        })
        uris = database_uris(default_uri)
        self._binds["default"] = Bind("default", uris, metadata=None, **engine_kwargs)

        further_binds = fluid.config.get("SQLALCHEMY_BINDS", {})
        for key, uri in further_binds.items():
            uris = database_uris(uri)
            self._binds[key] = Bind(key, uris, metadata=None, **engine_kwargs)

        SQLAlchemy._instance = self

    def _resolve_bind(self, bind_key, model):
        if not (bind_key or model): bind = self._binds["default"]
        elif bind_key: bind = self.get_bind(bind_key)
        else: bind = self.get_bind_for_model(model)
        return bind

    def get_bind(self, bind_key):
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
        try: yield self.current_executor
        except RuntimeError:
            with self.executor(bind_key, model) as e:
                yield e

    @asynccontextmanager
    async def ensured_async_executor(self, bind_key=None, model=None):
        try: yield self.current_async_executor
        except RuntimeError:
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
        return list(self._binds.keys())

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            raise FrameworkException("SQLAlchemy.expand_fluid() was never called!")
        return cls._instance
