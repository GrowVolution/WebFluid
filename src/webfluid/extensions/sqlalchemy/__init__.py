
__all__ = [
    "SQLAlchemy",

    "Model", "Bind", "Executor", "AsyncExecutor",
    "database_uris"
]


def __getattr__(name):
    if name == "SQLAlchemy":
        from .main import SQLAlchemy
        return SQLAlchemy

    if name == "Model":
        from .model import Model
        return Model

    if name == "Bind":
        from .bind import Bind
        return Bind

    if name in {"Executor", "AsyncExecutor"}:
        from . import executor
        return getattr(executor, name)

    if name == "database_uris":
        from .utils import database_uris
        return database_uris

    raise AttributeError(name)


def __dir__(): return sorted(__all__)
