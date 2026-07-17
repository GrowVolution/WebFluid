
__all__ = ["BaseContext", "FluidContext"]


def __getattr__(name):
    if name == "BaseContext":
        from .base import BaseContext
        return BaseContext

    if name == "FluidContext":
        from .fluid import FluidContext
        return FluidContext

    raise AttributeError(name)
