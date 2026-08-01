
__all__ = [
    "Security",

    "services", "models", "utils"
]


def __getattr__(name):
    if name == "Security":
        from .security import Security
        return Security

    if name in {"services", "models", "utils"}:
        from importlib import import_module
        return import_module(f".{name}", __name__)

    raise AttributeError(name)


def __dir__(): return sorted(__all__)
