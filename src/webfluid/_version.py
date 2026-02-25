from importlib.metadata import version as _version


class FluidVersion(tuple):
    def __new__(cls, major: int, minor: int, patch: int):
        return super().__new__(cls, (major, minor, patch))

    def __str__(self):
        return f"v{'.'.join(map(str, self))}"


def version() -> FluidVersion:
    v_str = _version("webfluid").split(" ")[-1].lstrip("v")
    return FluidVersion(*map(int, v_str.split(".")))
