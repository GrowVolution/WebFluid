from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid.core.fluid import Fluid
    from webfluid.core.additive import Additive, AdditiveVersion
    from webfluid.core.manifest import Manifest
    from webfluid.core.constants import *

__all__ = [
    "Fluid", "Additive",
    "Manifest", "AdditiveVersion",
    "ext", "context", "config",

    "FRAMEWORK_ROOT",
    "APP_STATIC", "WF_STATIC",
    "DEBUG", "TAILWIND", "PROCESSING",
    "EXT_SCHEDULING", "EXT_SQLALCHEMY",
    "EXT_BABEL", "EXT_CACHE", "EXT_MAIL", "EXT_JWT",
]


def __getattr__(name):
    if name == "Fluid":
        from .fluid import Fluid
        return Fluid

    if name in {"Additive", "AdditiveVersion"}:
        from . import additive
        return getattr(additive, name)

    if name == "Manifest":
        from .manifest import Manifest
        return Manifest

    if name in {
        "FRAMEWORK_ROOT",
        "APP_STATIC", "WF_STATIC",
        "DEBUG", "TAILWIND", "PROCESSING",
        "EXT_SCHEDULING", "EXT_SQLALCHEMY",
        "EXT_BABEL", "EXT_CACHE", "EXT_MAIL", "EXT_JWT"
    }:
        from . import constants
        return getattr(constants, name)

    raise AttributeError(name)
