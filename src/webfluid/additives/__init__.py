
__all__ = [
    "register_additives",
    "installed_additives", "installed_bases",
    "import_base"
]


def __getattr__(name):
    if name in {
        "register_additives",
        "installed_additives", "installed_bases",
        "import_base"
    }:
        from . import core
        return getattr(core, name)

    raise AttributeError(name)
