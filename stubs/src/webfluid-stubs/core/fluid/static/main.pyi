from os import PathLike
from pathlib import Path

from fastapi.staticfiles import StaticFiles as _StaticFiles

from webfluid import Fluid

class StaticFiles:
    _sources: list[tuple[str, _StaticFiles, str | None]]
    def __init__(self, fluid: Fluid) -> None: ...
    def add(
        self, path: str, directory: PathLike[str] | Path,
        name: str | None = None
    ) -> None: ...
    def mount(self, fluid: Fluid) -> None: ...
