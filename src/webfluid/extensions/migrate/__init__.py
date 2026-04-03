from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid.extensions.migrate.migrate import Migrate

__all__ = ["Migrate"]


def __getattr__(name):
    if name == "Migrate":
        from .migrate import Migrate
        return Migrate

    raise AttributeError(name)
