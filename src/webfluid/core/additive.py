from fastapi import APIRouter
from fastapi.datastructures import Default
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.utils import generate_unique_id
from jinja2 import PrefixLoader, FileSystemLoader, ChoiceLoader
from functools import wraps
from frozendict import frozendict
from pathlib import Path
import subprocess, sys, typer

from webfluid.core.context import FluidContext
from webfluid.core.constants import PROCESSING
from webfluid.surface.frontend import Frontend
from webfluid.utils.core import (final_version, get_root_path, required_arg_count,
                                 safe_execute, async_result, try_import)
from webfluid.utils.additives import require_extensions
from webfluid.utils.logging import factory as log_factory
from webfluid.exceptions import AdditiveException, ManifestError, OceanError


class AdditiveVersion(tuple):
    def __init__(self, major, minor=None, patch=None):
        if minor is None and patch is None:
            _, self.stage, self.build = final_version(major)
        elif minor is not None and patch is None:
            _, self.stage, self.build = final_version(minor)
        elif patch is not None:
            _, self.stage, self.build = final_version(patch)
        else: raise ValueError("Invalid version format.")

    def __new__(cls, major, minor=None, patch=None):
        if minor is None and patch is None: self = (final_version(major)[0],)
        elif patch is None: self = (int(major), final_version(minor)[0])
        else: self = (int(major), int(minor), final_version(patch)[0])
        return super().__new__(cls, self)

    def __str__(self):
        return (f"{'.'.join(map(str, self))}{self.stage}"
                f"{self.build if self.stage else ''}")


class AdditiveRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        self._fake_http_middleware = []
        super().__init__(*args, **kwargs)

    def http_middleware(self, fn):
        self._fake_http_middleware.append(fn)
        return fn

    def add_api_route(
        self, path, endpoint,
        *,
        response_model=Default(None), status_code=None,
        tags=None, dependencies=None,
        summary=None, description=None,
        response_description="Successful Response",
        responses=None, deprecated=None,
        methods=None, operation_id=None,
        response_model_include=None, response_model_exclude=None,
        response_model_by_alias=True, response_model_exclude_unset=False,
        response_model_exclude_defaults=False, response_model_exclude_none=False,
        include_in_schema=True, response_class=Default(JSONResponse),
        name=None, route_class_override=None,
        callbacks=None, openapi_extra=None,
        generate_unique_id_function=Default(generate_unique_id),
        strict_content_type=Default(True),
    ):

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

    def add_api_websocket_route(self, path, endpoint, name=None, *, dependencies=None):
        super().add_api_websocket_route(
            path, log_factory.additive_context(endpoint), name=name, dependencies=dependencies
        )


class Additive:
    def __init__(self, import_name, base=None, required_extensions=None):

        if not "additives." in import_name:
            raise AdditiveException("Additives have to be created inside the 'additives' package.")

        self.name = import_name.split(".")[-1]
        self.import_name = import_name
        self.root_path = Path(get_root_path(import_name)).resolve()

        from webfluid.core.manifest import Manifest
        try: self.manifest = Manifest(self.root_path / "manifest.json")
        except (FileNotFoundError, ManifestError) as e:
            print(e)
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

        async def enable(fluid):
            await self._before_enable(fluid)
            if base: await base._before_enable(fluid)

            self._enable(fluid)

            await self._after_enable()
            if base: await base._after_enable()

        if base: self.required_extensions.extend(base.required_extensions or [])
        self.enable = log_factory.additive_context(
            require_extensions(*self.required_extensions)(enable)
        )

        static_path = self.root_path / "static"
        self.static_files = None
        if static_path.exists():
            self.static_files = StaticFiles(directory=static_path)

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

        def middleware(call_next):
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
            def url_for(endpoint, **path_params):
                try:
                    ctx = FluidContext.current()
                    if not ctx.request: return None
                    fn = FluidContext.current().request.url_for
                except RuntimeError: return None

                external = path_params.pop("external", False)
                url = fn(self.unique_name(endpoint), **path_params)
                if external: return str(url)
                return url.path

            self.jinja_context["url_for"] = url_for
            self.context_processor(lambda: self.jinja_context)

    def __repr__(self):
        return f"<{self.name} {self.version}> {self.manifest.get('description', '')}"

    async def _before_enable(self, fluid):
        self._before_enable_lock = True
        for hook in self._hooks["before"]:
            await safe_execute(hook, False, fluid)

    def _enable(self, fluid):
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
            self.base.jinja_context["id"] = self.id
            self.base.jinja_context = frozendict(self.base.jinja_context)

        if self.frontend is not None:
            self.frontend.cover_additive(self)
            self.jinja_context["frontend"] = self.frontend.include
            fluid.static_prefixes.add(self.frontend.prefix)

        self.jinja_context["id"] = self.id
        self.jinja_context = frozendict(self.jinja_context)

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

    def before_enable(self, fn):
        if self._before_enable_lock:
            raise RuntimeError("Enable hooks cannot be added after the additive was enabled.")

        if required_arg_count(fn) != 1:
            raise TypeError(
                "Enable hooks (before) must receive exactly one non optional argument (type Fluid)."
            )

        self._hooks["before"].append(log_factory.additive_context(fn))
        return fn

    def after_enable(self, fn):
        if self._after_enable_lock:
            raise RuntimeError("Enable hooks cannot be added after the additive was enabled.")

        if required_arg_count(fn) > 0:
            raise TypeError("Enable hooks (after) must not receive non optional arguments.")

        self._hooks["after"].append(log_factory.additive_context(fn))
        return fn

    def context_processor(self, fn):
        if required_arg_count(fn) > 0:
            raise TypeError("Context processors must not receive non optional arguments.")
        self._context_processors.append(fn)
        return fn

    def before_request(self, fn):
        if required_arg_count(fn) > 0:
            raise TypeError("Before request processors must not receive non optional arguments.")
        self._request_processors["before"].append(fn)
        return fn

    def after_request(self, fn):
        if required_arg_count(fn) != 1:
            raise TypeError("After request processors must receive exactly one argument (response).")
        self._request_processors["after"].append(fn)
        return fn

    async def render(self, template, **ctx):
        if self.parent: return await self.parent.render(template, **ctx)

        for processor in self._context_processors:
            result = await safe_execute(processor, False)
            if not isinstance(result, dict): continue
            ctx = result | ctx
        c = FluidContext.current()
        return await c.fluid.render(f"{self.id}/{template}", **ctx)

    def unique_name(self, name):
        if self.parent: return self.parent.unique_name(name)
        return f"{self.id}_{name}"

    @staticmethod
    def _normalize_requirements(requirement):
        if isinstance(requirement, list):
            normalized = {}
            for entry in requirement:
                if not isinstance(entry, str): continue
                parts = entry.split("@")
                normalized[parts[0]] = parts[1] if len(parts) == 2 else "*"
            return normalized
        return requirement if isinstance(requirement, dict) else {}

    def _required_additives(self):
        if "requires" not in self.manifest: return {}
        return self._normalize_requirements(
            self.manifest["requires"].get("additives") or {}
        )

    @staticmethod
    def _match_version(meta, constraint):
        from webfluid.utils.core import check_required_version

        matching = []
        for release in meta.get("releases", []):
            version = release["version"]
            try:
                candidate = AdditiveVersion(*version.split("."))
                if candidate.stage != "": continue
                if constraint != "*" and not check_required_version(
                        constraint, "additive", candidate
                ): continue
                matching.append((tuple(candidate), version))
            except (ValueError, TypeError): continue

        if not matching: return None
        matching.sort()
        return matching[-1][1]

    def _pull_dependency(self, rid, constraint, additive_root, seen):
        from webfluid.utils.ocean import Ocean, extract_archive, humanize_error

        target = additive_root / rid
        if target.exists() and any(target.iterdir()): return

        ocean = Ocean()
        try: meta = ocean.resolve("additives", rid)
        except OceanError as e:
            typer.echo(typer.style(
                f"[{self.name}] Could not resolve required additive '{rid}': "
                f"{humanize_error(e.detail)}",
                fg=typer.colors.RED, bold=True
            ))
            return

        version = self._match_version(meta, constraint)
        if version is None:
            typer.echo(typer.style(
                f"[{self.name}] No stable release of '{rid}' matches '{constraint}'.",
                fg=typer.colors.RED, bold=True
            ))
            return

        if not meta.get("oss") and not meta.get("owned"):
            typer.echo(typer.style(
                f"[{self.name}] Required additive '{rid}' is paid and not owned. "
                "Install it manually with 'wf ocean install'.",
                fg=typer.colors.RED, bold=True
            ))
            return

        try: data = ocean.download("additives", rid, version)
        except OceanError as e:
            typer.echo(typer.style(
                f"[{self.name}] Failed to download '{rid}': "
                f"{humanize_error(e.detail)}",
                fg=typer.colors.RED, bold=True
            ))
            return

        extract_archive(data, target)
        typer.echo(typer.style(
            f"[{self.name}] Pulled required additive '{rid}' {version}.",
            fg=typer.colors.GREEN
        ))

        from importlib import import_module
        project_root = Path.cwd()
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        try:
            mod = import_module(f"additives.{target.name}")
            dependency = getattr(mod, "additive", None)
            if dependency is not None and not dependency.is_base:
                dependency.install(seen)
        except Exception as e:
            typer.echo(typer.style(
                f"[{self.name}] Failed to install pulled additive '{rid}': {e}",
                fg=typer.colors.RED, bold=True
            ))

    def _resolve_dependencies(self, seen):
        required = self._required_additives()
        if not required: return

        from webfluid.utils.core import check_required_version
        from webfluid.utils.additives import installed_additives, installed_bases

        additive_root = Path.cwd() / "additives"
        additive_root.mkdir(exist_ok=True)

        installed = {}
        for entry in installed_additives(additive_root, cache=False):
            installed[entry[0]] = entry[1]
        for entry in installed_bases(additive_root, cache=False):
            installed[entry[0]] = entry[1]

        for rid, constraint in required.items():
            if rid in seen: continue

            if rid in installed:
                version = installed[rid]
                try: matches = check_required_version(constraint, "additive", version)
                except ValueError: matches = True
                if not matches:
                    typer.echo(typer.style(
                        f"[{self.name}] Installed additive '{rid}' ({version}) does not "
                        f"match the required version '{constraint}'.",
                        fg=typer.colors.YELLOW, bold=True
                    ))
                continue

            self._pull_dependency(rid, constraint, additive_root, seen)

    def install(self, _seen=None):
        seen = _seen if _seen is not None else set()
        if self.id in seen: return
        seen.add(self.id)

        self._resolve_dependencies(seen)

        if self.base:
            self.base._extract()
            self.base._install_packages()
        self._extract()
        self._install_packages()

    def configure(self, config):
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
    def version(self):
        version_str = self.manifest["version"]
        return AdditiveVersion(*version_str.split("."))
