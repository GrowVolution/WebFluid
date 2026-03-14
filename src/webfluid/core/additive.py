from fastapi import APIRouter, params
from fastapi.datastructures import Default, DefaultPlaceholder
from fastapi.routing import APIRoute, BaseRoute
from fastapi.responses import Response, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.utils import generate_unique_id
from pydantic.main import IncEx
from jinja2 import PrefixLoader, FileSystemLoader
from functools import wraps
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Sequence, Any
import subprocess, sys, typer

from webfluid.core.manifest import Manifest
from webfluid.core.context import FluidContext
from webfluid.surface.frontend import Frontend
from webfluid.utils import get_root_path, safe_string, required_arg_count, safe_execute, async_result
from webfluid.utils.additive import require_extensions
from webfluid.utils.logging import factory as log_factory
from webfluid.exceptions import AdditiveException, ManifestError, EventHookException, ProcessorException

if TYPE_CHECKING:
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


class AdditiveRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        self._fake_http_middleware = []
        super().__init__(*args, **kwargs)

    def http_middleware(self, fn: Callable) -> Callable:
        self._fake_http_middleware.append(fn)
        return fn

    def add_api_route(
            self, path: str, endpoint: Callable[..., Any], *,
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

        @wraps(endpoint)
        async def wrapped(*args, **kwargs):
            handler = endpoint
            for middleware in reversed(self._fake_http_middleware):
                handler = middleware(handler)
            return await async_result(handler(*args, **kwargs))

        super().add_api_route(
            path, log_factory.additive_context(wrapped), response_model=response_model, status_code=status_code,
            tags=tags, dependencies=dependencies, summary=summary, description=description,
            response_description=response_description, responses=responses, deprecated=deprecated,
            methods=methods, operation_id=operation_id, response_model_include=response_model_include,
            response_model_exclude=response_model_exclude, response_model_by_alias=response_model_by_alias,
            response_model_exclude_unset=response_model_exclude_unset,
            response_model_exclude_defaults=response_model_exclude_defaults,
            response_model_exclude_none=response_model_exclude_none, include_in_schema=include_in_schema,
            response_class=response_class, name=name, route_class_override=route_class_override,
            callbacks=callbacks, openapi_extra=openapi_extra
        )

    def add_api_websocket_route(self, path: str, endpoint: Callable[..., Any], name: str | None = None,
                                *, dependencies: Sequence[params.Depends] | None = None):
        super().add_api_websocket_route(
            path, log_factory.additive_context(endpoint), name=name, dependencies=dependencies
        )


class Additive:
    def __init__(self, import_name: str, base: "Additive | None" = None,
                 required_extensions: list = None):

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
        self.prefix = f"/{self.name.replace('_', '-')}"

        self.is_base = self.manifest["type"] == "base"
        self.required_extensions = required_extensions or []

        if base and self.is_base:
            raise AdditiveException(f"[{self.additive_name}] Base additives cannot extend other additives.")
        elif base and not base.is_base:
            raise AdditiveException(f"[{self.additive_name}] Default additives can only extend base additives.")

        self.base = base
        self.parent = None

        async def enable(fluid: "Fluid"):
            await self._before_enable(fluid)
            self._enable(fluid)
            await self._after_enable()

        if base: self.required_extensions.extend(base.required_extensions or [])
        self.enable = log_factory.additive_context(
            require_extensions(*self.required_extensions)(enable)
        )

        self.static_files = StaticFiles(
            directory=(self.root_path / "static")
        )
        self.loader = PrefixLoader(
            { self.name: FileSystemLoader(self.root_path / "templates") }
        )
        self._context_processors = []
        self._request_processors = {
            "before": [],
            "after": []
        }
        self._hooks = {
            "before": [],
            "after": []
        }
        self._before_enable_lock = False
        self._after_enable_lock = False

        if self.is_base:
            self.api = AdditiveRouter()
            self.app = AdditiveRouter(default_response_class=HTMLResponse)
            self.ws = AdditiveRouter()
            self.frontend = None
        else:
            self.api = AdditiveRouter(prefix="/api")
            self.app = AdditiveRouter(default_response_class=HTMLResponse)
            self.ws = AdditiveRouter(prefix="/ws")
            self.frontend = Frontend()

        def middleware(call_next: Callable):
            async def wrapper(*args, **kwargs):
                c = FluidContext.current()
                for processor in self._request_processors["before"]:
                    response = await safe_execute(processor, ProcessorException, c.request)
                    if response is not None: return response
                response = await call_next(*args, **kwargs)
                for processor in reversed(self._request_processors["after"]):
                    response = await safe_execute(processor, ProcessorException, response)
                return response
            return wrapper

        self.api.http_middleware(middleware)
        self.app.http_middleware(middleware)

    def __repr__(self) -> str:
        return f"<{self.additive_name} {self.version}> {self.manifest.get('description', '')}"

    async def _before_enable(self, fluid: "Fluid"):
        self._before_enable_lock = True
        for hook in self._hooks["before"]:
            await safe_execute(hook, EventHookException, fluid)

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
            self.api.include_router(self.base.api)
            self.app.include_router(self.base.app)
            self.ws.include_router(self.base.ws)
            self.base.parent = self

        if self.frontend is not None:
            self.frontend.cover_additive(self)
            self.context_processor(lambda: {
                "frontend": self.frontend.include,
            })

        fluid.include_router(self.api, prefix=self.prefix)
        fluid.include_router(self.app, prefix=self.prefix)
        fluid.include_router(self.ws, prefix=self.prefix)
        fluid.mount(
            f"{self.prefix}/static", self.static_files,
            f"{self.name}_static"
        )

    async def _after_enable(self):
        self._after_enable_lock = True
        for hook in reversed(self._hooks["after"]):
            await safe_execute(hook, EventHookException)

    def _extract(self):
        extract_path = Path(self.root_path) / "extract"

        def for_dir(path, name):
            for file in (path / name).rglob("*"):
                if not file.is_file():
                    continue

                rel = file.relative_to(path)
                dst = Path.cwd() / "fluid" / rel
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

    def before_enable(self, fn: Callable) -> Callable:
        if self._before_enable_lock:
            raise RuntimeError("Enable hooks cannot be added after the additive was enabled.")

        if required_arg_count(fn) != 1:
            raise TypeError(
                "Enable hooks (before) must receive exactly one non optional argument (type Fluid)."
            )

        self._hooks["before"].append(log_factory.additive_context(fn))
        return fn

    def after_enable(self, fn: Callable) -> Callable:
        if self._after_enable_lock:
            raise RuntimeError("Enable hooks cannot be added after the additive was enabled.")

        if required_arg_count(fn) > 0:
            raise TypeError("Enable hooks (after) must not receive non optional arguments.")

        self._hooks["after"].append(log_factory.additive_context(fn))
        return fn

    def context_processor(self, fn: Callable) -> Callable:
        if required_arg_count(fn) > 0:
            raise TypeError("Context processors must not receive non optional arguments.")
        self._context_processors.append(fn)
        return fn

    def before_request(self, fn: Callable) -> Callable:
        if required_arg_count(fn) != 1:
            raise TypeError("Request processors must receive exactly one argument (request).")
        self._request_processors["before"].append(fn)
        return fn

    def after_request(self, fn: Callable) -> Callable:
        if required_arg_count(fn) != 1:
            raise TypeError("Request processors must receive exactly one argument (response).")
        self._request_processors["after"].append(fn)
        return fn

    async def render(self, template: str, **ctx) -> str:
        for processor in self._context_processors:
            result = await safe_execute(processor, ProcessorException)
            if not isinstance(result, dict): continue
            ctx = result | ctx
        c = FluidContext.current()
        return await c.fluid.render(f"{self.name}/{template}", **ctx)

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
