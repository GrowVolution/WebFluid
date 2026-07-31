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
                raise FrameworkException(
                    f"{type(instance).__name__}.expand_fluid() has not been called."
                )

        return target


class FluidExtension:
    def __init__(self, fluid=None, *args, **kwargs):
        if fluid is not None: self.expand_fluid(fluid, *args, **kwargs)

    def expand_fluid(self, fluid, *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def cli_entry(cls, app, name):
        if not hasattr(cls, "_cli"): return
        app.add_typer(cls._cli, name=name)
