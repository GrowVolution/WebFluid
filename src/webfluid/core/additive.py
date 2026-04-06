from fastapi import APIRouter, params
from fastapi.datastructures import Default, DefaultPlaceholder
from fastapi.routing import APIRoute, BaseRoute
from fastapi.responses import Response, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.utils import generate_unique_id
from pydantic.main import IncEx
from jinja2 import PrefixLoader, FileSystemLoader, ChoiceLoader
from functools import wraps
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Sequence, Any
import subprocess, sys, typer

from webfluid.core.context import FluidContext
from webfluid.core.constants import PROCESSING
from webfluid.surface.frontend import Frontend
from webfluid.utils.framework import (get_root_path, required_arg_count,
                                      safe_execute, async_result, try_import)
from webfluid.utils.logging import factory as log_factory
from webfluid.exceptions import AdditiveException, ManifestError

if TYPE_CHECKING:
    from configparser import ConfigParser
    from webfluid.core.fluid import Fluid


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
        self, path: str, endpoint: Callable[..., Any],
        *,
        response_model: Any = Default(None), status_code: int | None = None,
        tags: list[str | Enum] | None = None, dependencies: Sequence[params.Depends] | None = None,
        summary: str | None = None,  description: str | None = None,
        response_description: str = "Successful Response",
        responses: dict[int | str, dict[str, Any]] | None = None, deprecated: bool | None = None,
        methods: set[str] | list[str] | None = None, operation_id: str | None = None,
        response_model_include: IncEx | None = None, response_model_exclude: IncEx | None = None,
        response_model_by_alias: bool = True,  response_model_exclude_unset: bool = False,
        response_model_exclude_defaults: bool = False, response_model_exclude_none: bool = False,
        include_in_schema: bool = True, response_class: type[Response] | DefaultPlaceholder = Default(JSONResponse),
        name: str | None = None, route_class_override: type[APIRoute] | None = None,
        callbacks: list[BaseRoute] | None = None, openapi_extra: dict[str, Any] | None = None,
        generate_unique_id_function: Callable[[APIRoute], str] | DefaultPlaceholder = Default(generate_unique_id),
        strict_content_type: bool | DefaultPlaceholder = Default(True),
    ) -> None:

        @wraps(endpoint)
        async def wrapped(*args, **kwargs):
            handler = endpoint
            for middleware in reversed(self._fake_http_middleware):
                handler = middleware(handler)
            return await async_result(handler(*args, **kwargs))

        super().add_api_route(
            path, log_factory.additive_context(wrapped), response_model=response_model, status_code=status_code, tags=tags,
            dependencies=dependencies, summary=summary, description=description,
            response_description=response_description, responses=responses, deprecated=deprecated,
            methods=methods, operation_id=operation_id, response_model_include=response_model_include,
            response_model_exclude=response_model_exclude, response_model_by_alias=response_model_by_alias,
            response_model_exclude_unset=response_model_exclude_unset,
            response_model_exclude_defaults=response_model_exclude_defaults,
            response_model_exclude_none=response_model_exclude_none, include_in_schema=include_in_schema,
            response_class=response_class, name=name, route_class_override=route_class_override,
            callbacks=callbacks, openapi_extra=openapi_extra, generate_unique_id_function=generate_unique_id_function,
            strict_content_type=strict_content_type
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

        self.name = import_name.split(".")[-1]
        self.import_name = import_name
        self.root_path = Path(get_root_path(import_name)).resolve()

        from webfluid.core.manifest import Manifest
        try: self.manifest = Manifest(self.root_path / "manifest.json")
        except (FileNotFoundError, ManifestError) as e:
            raise AdditiveException(f"[{self.name}] Failed to load manifest: {e}")

        if not "name" in self.manifest:
            self.manifest["name"] = self.name
        else:
            self.name = self.manifest["name"]
        self.id = self.manifest["id"]
        self.prefix = f"/{self.id.replace('_', '-')}"

        self.is_base = self.manifest["type"] == "base"
        self.required_extensions = required_extensions or []

        if base and self.is_base:
            raise AdditiveException(f"[{self.name}] Base additives cannot extend other additives.")
        elif base and not base.is_base:
            raise AdditiveException(f"[{self.name}] Default additives can only extend base additives.")

        self.base = base
        self.parent = None

        async def enable(fluid: "Fluid"):
            await self._before_enable(fluid)
            if base: await base._before_enable(fluid)

            self._enable(fluid)

            await self._after_enable()
            if base: await base._after_enable()

        from webfluid.utils.additive import require_extensions
        if base: self.required_extensions.extend(base.required_extensions or [])
        self.enable = log_factory.additive_context(
            require_extensions(*self.required_extensions)(enable)
        )

        static_path = self.root_path / "static"
        self.static_files = None
        if static_path.exists():
            self.static_files = StaticFiles(
                directory=static_path
            )

        if base:
            self.loader = PrefixLoader(
                { self.id: ChoiceLoader([
                    FileSystemLoader(self.root_path / "templates"),
                    FileSystemLoader(base.root_path / "templates")
                ]) }
            )

        elif not self.is_base:
            self.loader = PrefixLoader(
                {self.id: FileSystemLoader(self.root_path / "templates")}
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
        self.jinja_context = {}

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
                for processor in self._request_processors["before"]:
                    response = await safe_execute(processor, True)
                    if response is not None: return response
                response = await safe_execute(call_next, True, *args, **kwargs)
                for processor in reversed(self._request_processors["after"]):
                    response = await safe_execute(processor, True, response)
                return response
            return wrapper

        self.api.http_middleware(middleware)
        self.app.http_middleware(middleware)

        if PROCESSING:
            def url_for(name: str, **path_params):
                ctx = FluidContext.current()
                return ctx.request.url_for(self.unique_name(name), **path_params)

            self.jinja_context["url_for"] = url_for
            self.context_processor(lambda: self.jinja_context)

    def __repr__(self) -> str:
        return f"<{self.name} {self.version}> {self.manifest.get('description', '')}"

    async def _before_enable(self, fluid: "Fluid"):
        self._before_enable_lock = True
        for hook in self._hooks["before"]:
            await safe_execute(hook, False, fluid)

    def _enable(self, fluid: "Fluid"):
        if self.is_base: raise AdditiveException(
            f"[{self.name}] Base additives are not allowed be enabled."
        )

        self.manifest.check_requirements(fluid.additive_root)

        if self.base and self.base.parent:
            raise AdditiveException(
                f"[{self.name}] Base additive '{self.base.name}' has already "
                f"been extended by '{self.base.parent.name}'."
            )
        elif self.base:
            self.base.manifest.check_requirements(fluid.additive_root)
            self.api.include_router(self.base.api)
            self.app.include_router(self.base.app)
            self.ws.include_router(self.base.ws)
            self.base.parent = self
            self.base.prefix = self.prefix

        if self.frontend is not None:
            self.frontend.cover_additive(self)
            self.jinja_context["frontend"] = self.frontend.include
            fluid.static_prefixes.add(self.frontend.prefix)

        fluid.include_router(self.api, prefix=self.prefix)
        fluid.include_router(self.app, prefix=self.prefix)
        fluid.include_router(self.ws, prefix=self.prefix)

        if self.static_files:
            static_prefix = f"{self.prefix}/static"
            fluid.static_prefixes.add(static_prefix)
            fluid.mount(
                static_prefix, self.static_files,
                f"{self.id}_static"
            )

    async def _after_enable(self):
        self._after_enable_lock = True
        for hook in reversed(self._hooks["after"]):
            await safe_execute(hook, False)

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
                        f"[{self.name}] Could not extract '{'/'.join(rel.parts)}': "
                        "File already exists.", fg=typer.colors.YELLOW
                    ))
                    continue

                typer.echo(f"[{self.name}] Extracting '{'/'.join(rel.parts)}'.")

                dst.write_bytes(
                    file.read_bytes()
                )

        for_dir(extract_path, "static")
        for_dir(extract_path, "templates")

        typer.echo(typer.style(
            f"[{self.name}] Finished extracting additives extract files to main app.",
            fg=typer.colors.GREEN, bold=True
        ))

    def _install_packages(self):
        if not "requires" in self.manifest: return
        requirements = self.manifest["requires"]
        if not "packages" in requirements: return

        packages = requirements["packages"]
        if not isinstance(packages, list):
            typer.echo(typer.style(
                f"[{self.name}] Invalid packages requirement type: {type(packages)}",
                fg=typer.colors.YELLOW, bold=True
            ))
            return

        for package in packages:
            typer.echo(f"[{self.name}] Installing required package '{package}'...")

            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", package],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                typer.echo(typer.style(
                    f"[{self.name}] Failed to install package '{package}': {result.stderr}",
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
        if required_arg_count(fn) > 0:
            raise TypeError("Before request processors must not receive non optional arguments.")
        self._request_processors["before"].append(fn)
        return fn

    def after_request(self, fn: Callable) -> Callable:
        if required_arg_count(fn) != 1:
            raise TypeError("After request processors must receive exactly one argument (response).")
        self._request_processors["after"].append(fn)
        return fn

    async def render(self, template: str, **ctx) -> str:
        if self.parent: return await self.parent.render(template, **ctx)

        for processor in self._context_processors:
            result = await safe_execute(processor, False)
            if not isinstance(result, dict): continue
            ctx = result | ctx
        c = FluidContext.current()
        return await c.fluid.render(f"{self.id}/{template}", **ctx)

    def unique_name(self, name: str) -> str:
        if self.parent: return self.parent.unique_name(name)
        return f"{self.id}_{name}"

    def install(self):
        if self.base:
            self.base._extract()
            self.base._install_packages()
        self._extract()
        self._install_packages()

    def configure(self, config: "ConfigParser"):
        if self.base: self.base.configure(config)

        mod = try_import(f"{self.import_name}.config")
        if mod is None: return

        setup = getattr(mod, "setup", None)
        if setup is None: return
        elif not isinstance(setup, dict):
            typer.secho(f"[{self.name}] Attribute 'setup' in '{self.import_name}.config' must be a dict.",
                        fg=typer.colors.YELLOW)
            return

        from webfluid.cli import questions
        config[self.id] = {}

        for key, settings in setup.items():
            if "type" not in settings:
                typer.secho(f"[{self.name}] Missing 'type' in setup settings for '{key}'.",
                            fg=typer.colors.YELLOW)
                continue
            elif settings["type"] not in {"select", "checkbox", "text", "confirm", "auto"}:
                typer.secho(f"[{self.name}] Invalid 'type' in setup settings for '{key}': {settings['type']}.",
                            fg=typer.colors.YELLOW)
                continue

            key_type = settings["type"]
            if key_type != "auto" and "message" not in settings:
                typer.secho(f"[{self.name}] Missing 'message' in setup settings for '{key}'.",
                            fg=typer.colors.YELLOW)
                continue
            elif key_type == "auto" and "value" not in settings:
                typer.secho(f"[{self.name}] Missing 'value' in setup settings for '{key}'.",
                            fg=typer.colors.YELLOW)
                continue

            if key_type == "auto":
                config[self.id][key] = settings["value"]
                continue

            question = getattr(questions, key_type)
            message = settings["message"]
            kwargs = settings.get("kwargs", {})

            config[self.id][key] = question(message, **kwargs).ask()

    @property
    def version(self) -> AdditiveVersion:
        version_str = self.manifest["version"]
        return AdditiveVersion(*map(int, version_str.split(".")))
