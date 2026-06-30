from collections.abc import Awaitable, Callable, Sequence
from enum import Enum
from pathlib import Path
from configparser import ConfigParser
from typing import Any

from fastapi import APIRouter, params
from fastapi.datastructures import DefaultPlaceholder
from fastapi.responses import Response
from fastapi.routing import APIRoute, BaseRoute
from fastapi.staticfiles import StaticFiles
from pydantic.main import IncEx
from jinja2 import PrefixLoader
from frozendict import frozendict

from webfluid import Fluid
from webfluid.core.manifest import Manifest
from webfluid.surface.frontend import Frontend

class AdditiveVersion(tuple[int, ...]):
    stage: str
    build: int
    def __init__(
        self, major: str, minor: str | None = None, patch: str | None = None
    ) -> None: ...
    def __new__(
        cls, major: str, minor: str | None = None, patch: str | None = None
    ) -> AdditiveVersion: ...
    def __str__(self) -> str: ...

class AdditiveRouter(APIRouter):
    _fake_http_middleware: list[Callable[..., Any]]
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def http_middleware(self, fn: Callable[..., Any]) -> Callable[..., Any]: ...
    def add_api_route(
        self, path: str, endpoint: Callable[..., Any],
        *,
        response_model: Any = ..., status_code: int | None = ...,
        tags: list[str | Enum] | None = ...,
        dependencies: Sequence[params.Depends] | None = ...,
        summary: str | None = ..., description: str | None = ...,
        response_description: str = ...,
        responses: dict[int | str, dict[str, Any]] | None = ...,
        deprecated: bool | None = ...,
        methods: set[str] | list[str] | None = ..., operation_id: str | None = ...,
        response_model_include: IncEx | None = ...,
        response_model_exclude: IncEx | None = ...,
        response_model_by_alias: bool = ...,
        response_model_exclude_unset: bool = ...,
        response_model_exclude_defaults: bool = ...,
        response_model_exclude_none: bool = ...,
        include_in_schema: bool = ...,
        response_class: type[Response] | DefaultPlaceholder = ...,
        name: str | None = ..., route_class_override: type[APIRoute] | None = ...,
        callbacks: list[BaseRoute] | None = ...,
        openapi_extra: dict[str, Any] | None = ...,
        generate_unique_id_function: Callable[[APIRoute], str] | DefaultPlaceholder = ...,
        strict_content_type: bool | DefaultPlaceholder = ...,
    ) -> None: ...
    def add_api_websocket_route(
        self, path: str, endpoint: Callable[..., Any], name: str | None = None,
        *, dependencies: Sequence[params.Depends] | None = None
    ) -> None: ...

class Additive:
    name: str
    import_name: str
    root_path: Path
    manifest: Manifest
    id: str
    prefix: str
    is_base: bool
    required_extensions: list[str]
    base: Additive | None
    parent: Additive | None
    enable: Callable[[Fluid], Awaitable[None]]
    static_files: StaticFiles | None
    loader: PrefixLoader
    jinja_context: dict[str, Any] | frozendict[str, Any]
    api: AdditiveRouter
    app: AdditiveRouter
    ws: AdditiveRouter
    frontend: Frontend | None
    def __init__(
        self, import_name: str, base: Additive | None = None,
        required_extensions: list[str] | None = None
    ) -> None: ...
    def __repr__(self) -> str: ...
    async def _before_enable(self, fluid: Fluid) -> None: ...
    def _enable(self, fluid: Fluid) -> None: ...
    async def _after_enable(self) -> None: ...
    def _extract(self) -> None: ...
    def _install_packages(self) -> None: ...
    def before_enable(self, fn: Callable[..., Any]) -> Callable[..., Any]: ...
    def after_enable(self, fn: Callable[..., Any]) -> Callable[..., Any]: ...
    def context_processor(self, fn: Callable[..., Any]) -> Callable[..., Any]: ...
    def before_request(self, fn: Callable[..., Any]) -> Callable[..., Any]: ...
    def after_request(self, fn: Callable[..., Any]) -> Callable[..., Any]: ...
    async def render(self, template: str, **ctx: Any) -> str: ...
    def unique_name(self, name: str) -> str: ...
    @staticmethod
    def _normalize_requirements(requirement: Any) -> dict[str, str]: ...
    def _required_additives(self) -> dict[str, str]: ...
    @staticmethod
    def _match_version(meta: dict[str, Any], constraint: str) -> str | None: ...
    def _pull_dependency(
        self, rid: str, constraint: str, additive_root: Path, seen: set[str]
    ) -> None: ...
    def _resolve_dependencies(self, seen: set[str]) -> None: ...
    def install(self, _seen: set[str] | None = None) -> None: ...
    def configure(self, config: ConfigParser) -> None: ...
    @property
    def version(self) -> AdditiveVersion: ...
