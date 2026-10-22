from abc import ABC, abstractmethod
from typing import Any

import typer

from webfluid import Fluid

class Delegated:
    path: list[str]
    optional: bool
    def __init__(self, path: str, optional: bool = False) -> None: ...
    def __get__(self, instance: object, owner: type | None = None) -> Any: ...

class FluidExtension(ABC):
    _cli: typer.Typer
    _unexpanded: str
    def __init__(self, fluid: Fluid | None = None, *args: Any, **kwargs: Any) -> None: ...
    @abstractmethod
    def expand_fluid(self, fluid: Fluid, *args: Any, **kwargs: Any) -> None: ...
    @classmethod
    def cli_entry(cls, app: typer.Typer, name: str) -> None: ...
    @classmethod
    def raise_unexpanded(cls) -> None: ...
