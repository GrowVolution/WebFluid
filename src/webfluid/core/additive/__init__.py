
__all__ = ["Additive", "Manifest"]


def __getattr__(name):
    if name == "Additive":
        from .main import Additive
        return Additive

    if name == "Manifest":
        from .manifest import Manifest
        return Manifest

    raise AttributeError(name)


def __dir__(): return sorted(__all__)
