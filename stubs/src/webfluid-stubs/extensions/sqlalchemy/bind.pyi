from collections.abc import AsyncIterator, Iterator
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from typing import Any

from sqlalchemy import Engine, MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker

class Bind:
    name: str
    sync_uri: str
    async_uri: str
    metadata: MetaData
    _options: dict[str, Any]
    _sync: tuple[Engine, sessionmaker[Session]] | None
    _async: tuple[AsyncEngine, async_sessionmaker[AsyncSession]] | None
    def __init__(
        self, key: str, uris: tuple[str, str],
        metadata: MetaData | None = None, **engine_kwargs: Any
    ) -> None: ...
    def _sync_bind(self) -> tuple[Engine, sessionmaker[Session]]: ...
    def _async_bind(self) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]: ...
    @property
    def sync_engine(self) -> Engine: ...
    @property
    def async_engine(self) -> AsyncEngine: ...
    async def dispose(self) -> None: ...
    def session(self) -> AbstractContextManager[Session]: ...
    def async_session(self) -> AbstractAsyncContextManager[AsyncSession]: ...
