__all__ = [
    "Fluid", "FluidVersion", "version",
    "Additive", "AdditiveVersion", "Manifest",
    "utils", "fluid", "extensions", "exceptions",
]


def __getattr__(name):
    if name in {"Fluid", "Additive", "AdditiveVersion", "Manifest"}:
        from webfluid import core
        return getattr(core, name)

    if name in {"FluidVersion", "version"}:
        from webfluid import _version
        return getattr(_version, name)

    raise AttributeError(name)
