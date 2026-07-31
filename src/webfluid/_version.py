from importlib.metadata import version as _version

from webfluid.utils.core.versioning import Version


class FluidVersion(Version): pass


def version():
    return FluidVersion(_version("webfluid").split(" ")[-1].lstrip("v"))
