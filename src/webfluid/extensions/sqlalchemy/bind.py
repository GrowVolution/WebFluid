from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from contextlib import asynccontextmanager, contextmanager


class Bind:
    def __init__(self, key, uris, metadata=None, **engine_kwargs):
        from .model import Model

        self.name = key
        self.sync_uri, self.async_uri = uris
        self.metadata = metadata if metadata else Model.metadata_for(key)

        self._options = engine_kwargs
        self._sync = None
        self._async = None

    def _sync_bind(self):
        if self._sync is None:
            engine = create_engine(self.sync_uri, **self._options)
            self._sync = (engine, sessionmaker(engine, expire_on_commit=False))
        return self._sync

    def _async_bind(self):
        if self._async is None:
            engine = create_async_engine(self.async_uri, **self._options)
            self._async = (
                engine, async_sessionmaker(engine, expire_on_commit=False)
            )
        return self._async

    @property
    def sync_engine(self): return self._sync_bind()[0]

    @property
    def async_engine(self): return self._async_bind()[0]

    async def dispose(self):
        if self._sync is not None:
            self._sync[0].dispose()
            self._sync = None

        if self._async is not None:
            await self._async[0].dispose()
            self._async = None

    @contextmanager
    def session(self):
        with self._sync_bind()[1]() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

    @asynccontextmanager
    async def async_session(self):
        async with self._async_bind()[1]() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
