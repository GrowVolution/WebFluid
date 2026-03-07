from fastapi import APIRouter, params
from fastapi.datastructures import Default, DefaultPlaceholder
from fastapi.routing import APIRoute, BaseRoute
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.utils import generate_unique_id
from pydantic.main import IncEx
from jinja2 import PrefixLoader, FileSystemLoader
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Sequence, Any
import subprocess, sys, typer

from webfluid.core.manifest import Manifest
from webfluid.core.context import FluidContext
from webfluid.utils import get_root_path, safe_string
from webfluid.utils.additive import require_extensions
from webfluid.utils.logging import factory as log_factory
from webfluid.exceptions import AdditiveException, ManifestError

if TYPE_CHECKING:
    from fastapi.responses import HTMLResponse
    from webfluid import Fluid


class AdditiveVersion(tuple):
    def __new__(cls, major: int, minor: int | None = None, patch: int | None = None):
        minor = 0 if minor is None else minor
        patch = 0 if patch is None else patch
        return super().__new__(cls, (major, minor, patch))

    @property
    def length(self) -> int:
        if self[2] != 0:
            return 3
        if self[1] != 0:
            return 2
        return 1

    def __str__(self) -> str:
        return f"v{'.'.join(map(str, self[:self.length]))}"


class Additive(APIRouter):
    def __init__(self, import_name: str, base: "Additive",
                 required_extensions: list = None, allow_frontend: bool = True,
                 **router_kwargs):

        if not "additives." in import_name:
            raise AdditiveException("Additives have to be created inside the 'additives' package.")

        self.additive_name = import_name.split(".")[-1]
        self.import_name = import_name
        self.root_path = Path(get_root_path(import_name)).resolve()

        try: self.manifest = Manifest(self.root_path / "manifest.json")
        except (FileNotFoundError, ManifestError) as e:
            raise AdditiveException(f"[{self.additive_name}] Failed to load manifest: {e}")

        if not "name" in self.manifest:
            self.manifest["name"] = self.additive_name
        else:
            self.additive_name = self.manifest["name"]
        self.name = safe_string(self.additive_name)

        self.is_base = self.manifest["type"] == "base"
        self.required_extensions = required_extensions or []

        if base and self.is_base:
            raise AdditiveException(f"[{self.additive_name}] Base additives cannot extend other additives.")
        elif base and not base.is_base:
            raise AdditiveException(f"[{self.additive_name}] Default additives can only extend base additives.")

        self.base = base
        self.parent = None

        if base: self.required_extensions.extend(base.required_extensions or [])
        self.enable = log_factory.additive_context(
            require_extensions(*self.required_extensions)(self._enable)
        )

        self.static_files = StaticFiles(
            directory=(self.root_path / "static")
        )
        self.loader = PrefixLoader(
            { self.name: FileSystemLoader(self.root_path / "templates") }
        )

        self._allow_frontend = allow_frontend
        self._handlers = {}

        super().__init__(**router_kwargs)

    def __repr__(self) -> str:
        return f"<{self.additive_name} {self.version}> {self.manifest.get('description', '')}"


    def _enable(self, fluid: "Fluid"):
        if self.is_base: raise AdditiveException(
            f"[{self.additive_name}] Base additives are not allowed be enabled."
        )

        self.manifest.check_requirements(fluid.additive_root)

        if self.base and self.base.parent:
            raise AdditiveException(
                f"[{self.additive_name}] Base additive '{self.base.additive_name}' has already "
                f"been extended by '{self.base.parent.additive_name}'."
            )
        elif self.base:
            self.base.manifest.check_requirements(fluid.additive_root)
            self.include_router(self.base, prefix="/base")
            self.base.parent = self

        fluid.include_router(self, prefix=self.name)
        fluid.mount(
            f"/{self.name.replace('_', '-')}/static",
            self.static_files, f"{self.name}_static"
        )

    async def render(self, template: str, **ctx) -> "HTMLResponse":
        c = FluidContext.current()
        return await c.fluid.render(f"{self.name}/{template}", **ctx)

    def _extract(self):
        extract_path = Path(self.root_path) / "extract"

        def for_dir(path, name):
            for file in (path / name).rglob("*"):
                if not file.is_file():
                    continue

                rel = file.relative_to(path)
                dst = Path.cwd() / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists():
                    typer.echo(typer.style(
                        f"[{self.additive_name}] Could not extract '{'/'.join(rel.parts)}': "
                        "File already exists.", fg=typer.colors.YELLOW
                    ))
                    continue

                typer.echo(f"[{self.additive_name}] Extracting '{'/'.join(rel.parts)}'.")

                dst.write_bytes(
                    file.read_bytes()
                )

        for_dir(extract_path, "static")
        for_dir(extract_path, "templates")

        typer.echo(typer.style(
            f"[{self.additive_name}] Finished extracting additives extract files to main app.",
            fg=typer.colors.GREEN, bold=True
        ))

    def _install_packages(self):
        if not "requires" in self.manifest: return
        requirements = self.manifest["requires"]
        if not "packages" in requirements: return

        packages = requirements["packages"]
        if not isinstance(packages, list):
            typer.echo(typer.style(
                f"[{self.additive_name}] Invalid packages requirement type: {type(packages)}",
                fg=typer.colors.YELLOW, bold=True
            ))
            return

        for package in packages:
            typer.echo(f"[{self.additive_name}] Installing required package '{package}'...")

            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", package],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                typer.echo(typer.style(
                    f"[{self.additive_name}] Failed to install package '{package}': {result.stderr}",
                    fg=typer.colors.RED, bold=True
                ))

    def add_api_route(self, path: str, endpoint: Callable[..., Any], *,
                      response_model: Any = Default(None), status_code: int | None = None,
                      tags: list[str | Enum] | None = None, dependencies: Sequence[params.Depends] | None = None,
                      summary: str | None = None, description: str | None = None, response_description: str = "Successful Response",
                      responses: dict[int | str, dict[str, Any]] | None = None, deprecated: bool | None = None,
                      methods: set[str] | list[str] | None = None, operation_id: str | None = None,
                      response_model_include: IncEx | None = None, response_model_exclude: IncEx | None = None,
                      response_model_by_alias: bool = True, response_model_exclude_unset: bool = False,
                      response_model_exclude_defaults: bool = False, response_model_exclude_none: bool = False,
                      include_in_schema: bool = True, response_class: type[Response] | DefaultPlaceholder = Default(JSONResponse),
                      name: str | None = None, route_class_override: type[APIRoute] | None = None,
                      callbacks: list[BaseRoute] | None = None, openapi_extra: dict[str, Any] | None = None,
                      generate_unique_id_function: Callable[[APIRoute], str] | DefaultPlaceholder = Default(generate_unique_id)
                      ):
        super().add_api_route(
            path, log_factory.additive_context(endpoint), response_model=response_model, status_code=status_code,
            tags=tags, dependencies=dependencies, summary=summary, description=description,
            response_description=response_description, responses=responses, deprecated=deprecated,
            methods=methods, operation_id=operation_id, response_model_include=response_model_include,
            response_model_exclude=response_model_exclude, response_model_by_alias=response_model_by_alias,
            response_model_exclude_unset=response_model_exclude_unset,
            response_model_exclude_defaults=response_model_exclude_defaults,
            response_model_exclude_none=response_model_exclude_none, include_in_schema=include_in_schema,
            response_class=response_class, name=name, route_class_override=route_class_override,
            callbacks=callbacks, openapi_extra=openapi_extra,
        )

    def install(self):
        if self.base:
            self.base._extract()
            self.base._install_packages()
        self._extract()
        self._install_packages()

    @property
    def version(self) -> AdditiveVersion:
        version_str = self.manifest["version"]
        return AdditiveVersion(*map(int, version_str.split(".")))
