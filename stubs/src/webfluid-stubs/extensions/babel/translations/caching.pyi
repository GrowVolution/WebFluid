import asyncio
from collections.abc import Callable, Iterable
from typing import Any

from webfluid.extensions.babel.translations.models import I18nMessage

_Lock = Callable[[str, str], asyncio.Lock]
_Forms = dict[str, dict[str, str]]


class Cache:
    _db_cache: dict[str, dict[str, dict[str, Any]]]
    _uncached: dict[str, set[str]]
    _locale: str
    _domain: str
    def __init__(self, locale: str, domain: str) -> None: ...
    def is_uncached(self, key: str) -> bool: ...
    def get(self, key: str, num: int, ctx: str | None) -> str | None: ...
    async def uncache(self, key: str, lock: _Lock) -> None: ...
    async def recache(
        self, key: str,
        by_locale: dict[str, list[tuple[str, str | None, str]]],
        lock: _Lock
    ) -> None: ...
    @classmethod
    def _ensure_cache(cls, locale: str, domain: str) -> None: ...
    @classmethod
    def already_loaded(cls, locale: str, domain: str) -> bool: ...
    @classmethod
    def set(
        cls, locale: str, domain: str, key: str,
        message: str, pf: str, ctx: str | None
    ) -> None: ...
    @classmethod
    def locale_cache(cls, locale: str) -> dict[str, Any] | None: ...
    @classmethod
    def db_load(
        cls, locale: str, domain: str, messages: Iterable[I18nMessage]
    ) -> None: ...
    @classmethod
    def update(cls, locale: str, domain: str, keys: dict[str, _Forms]) -> None: ...
