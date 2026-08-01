
__all__ = [
    "Fluid", "Additive", "Manifest",

    "ext", "context", "constants", "config"
]


def __getattr__(name):
    if name == "Fluid":
        from .fluid import Fluid
        return Fluid

    if name == "Additive":
        from .additive import Additive
        return Additive

    if name == "Manifest":
        from .additive import Manifest
        return Manifest

    if name in {"ext", "context", "constants", "config"}:
        from importlib import import_module
        return import_module(f".{name}", __name__)

    raise AttributeError(name)


def __dir__(): return sorted(__all__)
