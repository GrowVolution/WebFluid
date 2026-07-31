from pathlib import Path
from typing import Any

from markupsafe import Markup

from webfluid import Additive, Fluid
from webfluid.surface.frontend.vite import Vite

_static_js: str

class Frontend:
    htmx: str
    alpine: str
    type: str
    prefix: str
    rel: str
    tailwind: str
    _vite: Vite | None
    _root: Path | None
    _static: Path | None
    _covered: bool
    _raw_tailwind: str
    def __init__(
        self, fluid: Fluid | None = None, additive: Additive | None = None
    ) -> None: ...
    @property
    def has_vite(self) -> bool: ...
    def _cover(self) -> None: ...
    def _init(
        self, frontend: dict[str, Any], root_path: Path, name: str = "app"
    ) -> None: ...
    def generate_tailwind(self, frontend: bool, static: bool) -> None: ...
    def cover_fluid(self, fluid: Fluid) -> None: ...
    def cover_additive(self, additive: Additive) -> None: ...
    def include(self) -> Markup: ...
    async def vite(self) -> Any: ...
    @classmethod
    def prepare(cls, fluid: Fluid) -> None: ...
