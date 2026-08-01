from importlib.metadata import version as _version

from webfluid.core.identity import FRAMEWORK_PACKAGE
from webfluid.utils.core.versioning import Version


def version():
    return Version(
        _version(FRAMEWORK_PACKAGE)
        .split(" ")[-1].lstrip("v")
    )
