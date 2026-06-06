from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .user import *
    from .token import *

__all__ = [
    "User", "Identity",
    "Role", "Permission",

    "ExpiredToken"
]


def __getattr__(name):
    if name in {
        "User", "Identity",
        "Role", "Permission"
    }:
        from . import user
        return getattr(user, name)

    if name == "ExpiredToken":
        from .token import ExpiredToken
        return ExpiredToken

    raise AttributeError(name)
