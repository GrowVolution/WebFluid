from collections.abc import Callable
from pathlib import Path
from typing import Any

from markupsafe import Markup

from webfluid import Fluid, Additive
from webfluid.surface.frontend.vite import Vite

_static_js: str

class Frontend:
    htmx: str
    alpine: str | bool
    type: str
    prefix: str
    rel: str
    tailwind: str
    generate_tailwind: Callable[..., Any]
    _vite: Vite
    def __init__(
        self, fluid: Fluid | None = None, additive: Additive | None = None
    ) -> None: ...
    def _init(
        self, frontend: dict[str, Any], root_path: Path, name: str = "app"
    ) -> None: ...
    def cover_fluid(self, fluid: Fluid) -> None: ...
    def cover_additive(self, additive: Additive) -> None: ...
    def include(self) -> Markup: ...
    @property
    def vite(self) -> Callable[..., Any]: ...
    @classmethod
    def prepare(cls, fluid: Fluid) -> None: ...
