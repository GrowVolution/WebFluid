from collections.abc import Callable, Sequence
from enum import Enum
from typing import Any

from fastapi import APIRouter, params
from fastapi.datastructures import DefaultPlaceholder
from fastapi.responses import Response
from fastapi.routing import APIRoute, BaseRoute
from pydantic.main import IncEx

class Router(APIRouter):
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
