from pathlib import Path
from typing import Any

from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles as _StaticFiles

from webfluid import Fluid

_STATIC: str

class CachedStaticFiles(_StaticFiles):
    max_age: int
    def __init__(self, *args: Any, max_age: int = 0, **kwargs: Any) -> None: ...
    def file_response(self, *args: Any, **kwargs: Any) -> Response: ...

class StaticFiles:
    _sources: list[tuple[str, CachedStaticFiles, str | None]]
    _max_age: int
    def __init__(self, fluid: Fluid) -> None: ...
    def add(self, path: str, directory: Path, name: str | None = None) -> None: ...
    def mount(self, fluid: Fluid) -> None: ...
