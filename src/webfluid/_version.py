from importlib.metadata import version as _version

from webfluid.utils.core import final_version


class FluidVersion(tuple):
    def __init__(self, major, minor, patch):
        _, self.stage, self.build = final_version(patch)

    def __new__(cls, major, minor, patch):
        return super().__new__(cls, (
            int(major), int(minor),
            final_version(patch)[0]
        ))

    def __str__(self):
        return (f"{'.'.join(map(str, self))}{self.stage}"
                f"{self.build if self.stage else ''}")


def version():
    v_str = _version("webfluid").split(" ")[-1].lstrip("v")
    return FluidVersion(*v_str.split("."))
