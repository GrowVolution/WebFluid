from fastapi import APIRouter
from fastapi.datastructures import Default
from fastapi.responses import JSONResponse
from fastapi.utils import generate_unique_id
from functools import wraps

from webfluid.utils.core import async_result
from webfluid.utils.logging import factory as log_factory


class Router(APIRouter):
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
