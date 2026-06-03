from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid.extensions.security.security import Security

__all__ = [
    "Security",

    "services", "models", "utils"
]


def __getattr__(name):
    if name == "Security":
        from .security import Security
        return Security

    raise AttributeError(name)
