from typing import TYPE_CHECKING, Optional
import typer

if TYPE_CHECKING:
    from webfluid.core.fluid import Fluid


class FluidExtension:
    _cli: typer.Typer

    def __init__(self, fluid: Optional["Fluid"] = None, *args, **kwargs):
        if fluid is not None: self.expand_fluid(fluid, *args)

    def expand_fluid(self, fluid: "Fluid", *args, **kwargs):
        raise NotImplementedError()

    @classmethod
    def cli_entry(cls, app: typer.Typer, name: str):
        if not hasattr(cls, "_cli"): return
        app.add_typer(cls._cli, name=name)
