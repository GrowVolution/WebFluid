from typing import Any

import typer

from webfluid import Fluid

class Delegated:
    path: list[str]
    optional: bool
    def __init__(self, path: str, optional: bool = False) -> None: ...
    def __get__(self, instance: object, owner: type | None = None) -> Any: ...

class FluidExtension:
    _cli: typer.Typer
    def __init__(self, fluid: Fluid | None = None, *args: Any, **kwargs: Any) -> None: ...
    def expand_fluid(self, fluid: Fluid, *args: Any, **kwargs: Any) -> None: ...
    @classmethod
    def cli_entry(cls, app: typer.Typer, name: str) -> None: ...
