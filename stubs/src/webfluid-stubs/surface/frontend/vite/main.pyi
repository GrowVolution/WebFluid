from pathlib import Path
from typing import Any

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from webfluid import Fluid
from webfluid.core.additive.router import Router

class Vite:
    _static_files: dict[str, tuple[str, StaticFiles]]
    _namespaces: set[str]
    root: Path
    rel: str
    dist: Path
    src: Path
    framework: str
    typescript: bool
    register_index: bool
    def __init__(
        self, root_path: Path, relative_path: str, config: dict[str, Any]
    ) -> None: ...
    async def index(self) -> str: ...
    async def response(self) -> HTMLResponse: ...
    def add_static(self, name: str, prefix: str) -> None: ...
    def generate_tailwind(self, raw_tailwind: str) -> None: ...
    def register(self, target: Fluid | Router) -> None: ...
    @classmethod
    def prepare(cls, fluid: Fluid) -> None: ...
