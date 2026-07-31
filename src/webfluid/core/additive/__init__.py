
__all__ = ["Additive", "Manifest", "AdditiveVersion"]


def __getattr__(name):
    if name == "Additive":
        from .main import Additive
        return Additive

    if name == "Manifest":
        from .manifest import Manifest
        return Manifest

    if name == "AdditiveVersion":
        from .version import Version
        return Version

    raise AttributeError(name)
