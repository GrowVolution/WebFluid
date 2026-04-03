from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid.cli.wf import cli

__all__ = ["cli"]


def __getattr__(name):
    if name == "cli":
        from .wf import cli
        return cli

    raise AttributeError(name)
