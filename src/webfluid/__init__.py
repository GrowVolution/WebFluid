from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid._version import FluidVersion, version
    from webfluid.core.fluid import Fluid
    from webfluid.core.additive import Additive, AdditiveVersion
    from webfluid.core.manifest import Manifest


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
