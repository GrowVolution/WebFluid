
__all__ = [
    "Fluid", "Additive",
    "Manifest", "AdditiveVersion",

    "ext", "context", "constants", "config"
]


def __getattr__(name):
    if name == "Fluid":
        from .fluid import Fluid
        return Fluid

    if name in {"Additive", "AdditiveVersion"}:
        from . import additive
        return getattr(additive, name)

    if name == "Manifest":
        from .additive import Manifest
        return Manifest

    raise AttributeError(name)
