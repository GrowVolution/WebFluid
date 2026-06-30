from collections.abc import Callable
from pathlib import Path
from typing import Any
import subprocess

from fastapi import Request, Response
from fastapi.staticfiles import StaticFiles
from markupsafe import Markup

from webfluid import Fluid, Additive

_static_js: Path

def _download_file(url: str, dest: Path) -> None: ...
def setup_frontend(project: str) -> None: ...
def validate_config(f: dict[str, Any]) -> tuple[bool, str | dict[str, Any]]: ...

class Frontend:
    _static_js: str
    _app_root: Path
    _proc: subprocess.Popen[Any]
    _dev_server: str
    _dev_prefix: str
    _static_files: dict[str, tuple[str, StaticFiles]]
    htmx: str
    alpine: str | bool
    type: str
    framework: str
    typescript: bool
    register_index: bool
    prefix: str
    root: Path
    dist: Path
    rel: str
    generate_tailwind: Callable[..., Any]
    tailwind: str
    def __init__(
        self, fluid: Fluid | None = None, additive: Additive | None = None
    ) -> None: ...
    def _init(
        self, frontend: dict[str, Any], root_path: Path, name: str = "app"
    ) -> None: ...
    async def _updated_index(self, index: str) -> str: ...
    async def _vite(self) -> str: ...
    def cover_fluid(self, fluid: Fluid) -> None: ...
    def cover_additive(self, additive: Additive) -> None: ...
    def include(self) -> Markup: ...
    async def vite(self) -> Response: ...
    @classmethod
    def prepare(cls, fluid: Fluid) -> None: ...
    @classmethod
    def stop(cls) -> None: ...
    @classmethod
    async def _asset_catch(cls, request: Request, path: str) -> Response: ...
