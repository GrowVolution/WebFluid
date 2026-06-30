__all__ = ["Migrate"]


def __getattr__(name):
    if name == "Migrate":
        from .migrate import Migrate
        return Migrate

    raise AttributeError(name)
