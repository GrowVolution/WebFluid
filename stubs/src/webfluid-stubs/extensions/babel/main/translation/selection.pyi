from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any
from zoneinfo import ZoneInfo

from babel import Locale


class Selector:
    _locale_selector_fn: Callable[..., Any] | None
    _timezone_selector_fn: Callable[..., Any] | None
    def __init__(self) -> None: ...
    def locale_selector(self, fn: Callable[..., Any]) -> Callable[..., Any]: ...
    def timezone_selector(self, fn: Callable[..., Any]) -> Callable[..., Any]: ...
    @property
    def locale_selector_fn(self) -> Callable[..., Any] | None: ...
    @property
    def timezone_selector_fn(self) -> Callable[..., Any] | None: ...
    @staticmethod
    @contextmanager
    def force(
        locale: str | Locale | None = None, timezone: str | ZoneInfo | None = None
    ) -> Iterator[None]: ...
    @staticmethod
    @asynccontextmanager
    def aforce(
        locale: str | Locale | None = None, timezone: str | ZoneInfo | None = None
    ) -> AsyncIterator[None]: ...
