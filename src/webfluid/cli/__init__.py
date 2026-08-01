
__all__ = ["cli"]


def __getattr__(name):
    if name == "cli":
        from .wf import cli
        return cli

    raise AttributeError(name)


def __dir__(): return sorted(__all__)
