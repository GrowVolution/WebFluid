from contextlib import AbstractContextManager, AbstractAsyncContextManager
from typing import Any

from sqlalchemy import MetaData, Engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


class Bind:
    name: str
    metadata: MetaData
    sync_engine: Engine
    async_engine: AsyncEngine
    def __init__(
        self, key: str, uris: tuple[str, str],
        metadata: MetaData | None = None, **engine_kwargs: Any
    ) -> None: ...
    def session(self) -> AbstractContextManager[Session]: ...
    def async_session(self) -> AbstractAsyncContextManager[AsyncSession]: ...
