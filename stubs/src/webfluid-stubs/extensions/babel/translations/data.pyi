import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from webfluid.extensions.babel.translations.caching import Cache
from webfluid.extensions.sqlalchemy.executor import AsyncExecutor

_Forms = dict[str, dict[str, str]]
_Translations = Callable[[], dict[str, dict[str, _Forms]]]


async def _retry_locked(
    fn: Callable[[], Awaitable[Any]], *, attempts: int = 6, delay: float = 0.1
) -> Any: ...
async def _write(
    e: AsyncExecutor, locale: str, kid: int,
    msg: str, pf: str, ctx: str | None
) -> None: ...


class TransactionService:
    _locks: dict[str, dict[str, asyncio.Lock]]
    _locale: str
    _domain: str
    _cache: Cache
    def __init__(self, locale: str, domain: str) -> None: ...
    def _fetch(self, key: str, num: int, ctx: str | None) -> str | None: ...
    def get(self, key: str, num: int = 1, ctx: str | None = None) -> str | None: ...
    async def uncache(self, key: str) -> None: ...
    async def recache(self, key: str) -> None: ...
    @classmethod
    def _ensure_lock(cls, locale: str, domain: str) -> asyncio.Lock: ...
    @classmethod
    async def kid(cls, domain: str, key: str) -> int: ...
    @classmethod
    async def resolve_keys(cls, domain: str, keys: set[str]) -> dict[str, int]: ...
    @classmethod
    async def set(
        cls, locale: str, domain: str, key: str,
        message: str, pf: str, ctx: str | None
    ) -> None: ...
    @classmethod
    async def load(cls, locale: str, domain: str) -> None: ...
    @classmethod
    async def update(cls, domain: str, translations: _Translations) -> None: ...
