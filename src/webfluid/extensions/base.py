

class FluidExtension:
    def __init__(self, fluid=None, *args, **kwargs):
        if fluid is not None: self.expand_fluid(fluid, *args, **kwargs)

    def expand_fluid(self, fluid, *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def cli_entry(cls, app, name):
        if not hasattr(cls, "_cli"): return
        app.add_typer(cls._cli, name=name)
