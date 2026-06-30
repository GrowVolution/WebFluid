from typing import Any

import typer

from webfluid import Fluid

class FluidExtension:
    _cli: typer.Typer
    def __init__(self, fluid: Fluid | None = None, *args: Any, **kwargs: Any) -> None: ...
    def expand_fluid(self, fluid: Fluid, *args: Any, **kwargs: Any) -> None: ...
    @classmethod
    def cli_entry(cls, app: typer.Typer, name: str) -> None: ...
