from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

from webfluid.core.context.base import BaseContext
from webfluid.extensions.babel.domain import Domain


class DomainContext(BaseContext):
    _ctx: ContextVar[Any]
    domain: Domain
    def __init__(self, domain: Domain) -> None: ...


class SelectorContext(BaseContext):
    _ctx: ContextVar[Any]
    locale_selector: Callable[..., Any] | None
    timezone_selector: Callable[..., Any] | None
    def __init__(
        self,
        locale_selector: Callable[..., Any] | None,
        timezone_selector: Callable[..., Any] | None,
    ) -> None: ...
