
__all__ = [
    "Fluid", "version",
    "Additive", "Manifest",
    "utils", "fluid", "extensions", "exceptions",
]

def __getattr__(name):
    if name in {"Fluid", "Additive", "Manifest"}:
        from webfluid import core
        return getattr(core, name)

    if name == "version":
        from ._version import version
        return version

    if name in {"utils", "fluid", "extensions", "exceptions"}:
        from importlib import import_module
        return import_module(f".{name}", __name__)

    raise AttributeError(name)


def __dir__(): return sorted(__all__)
