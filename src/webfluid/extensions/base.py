from abc import ABC, abstractmethod

from webfluid.exceptions import FrameworkException


class Delegated:
    def __init__(self, path, optional=False):
        self.path = path.split(".")
        self.optional = optional

    def __get__(self, instance, owner=None):
        if instance is None: return self

        target = instance
        last = len(self.path) - 1

        for index, attribute in enumerate(self.path):
            target = getattr(target, attribute)
            if target is None and not (self.optional and index == last):
                instance.raise_unexpanded()

        return target


class FluidExtension(ABC):
    _unexpanded = "{instance}.expand_fluid() has never been called."

    def __init__(self, fluid=None, *args, **kwargs):
        if fluid is not None: self.expand_fluid(fluid, *args, **kwargs)

    @abstractmethod
    def expand_fluid(self, fluid, *args, **kwargs): ...

    @classmethod
    def cli_entry(cls, app, name):
        if not hasattr(cls, "_cli"): return
        app.add_typer(cls._cli, name=name)

    @classmethod
    def raise_unexpanded(cls):
        raise FrameworkException(
            cls._unexpanded.format(instance=cls.__name__)
        )
