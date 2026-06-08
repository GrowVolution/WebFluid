from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid.additives.utils import *

__all__ = [
    "installed_additives", "installed_bases",
    "import_base",
]


def __getattr__(name):
    if name in {
        "installed_additives", "installed_bases",
        "import_base"
    }:
        from . import utils
        return getattr(utils, name)

    raise AttributeError(name)
