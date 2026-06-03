from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid.extensions.sqlalchemy.sqlalchemy import SQLAlchemy
    from webfluid.extensions.sqlalchemy.utils import *

__all__ = [
    "SQLAlchemy",

    "Model", "Bind", "Executor", "AsyncExecutor",
    "database_uris"
]


def __getattr__(name):
    if name == "SQLAlchemy":
        from .sqlalchemy import SQLAlchemy
        return SQLAlchemy

    if name in {
        "Model", "Bind", "Executor", "AsyncExecutor",
        "database_uris"
    }:
        from . import utils
        return getattr(utils, name)

    raise AttributeError(name)
