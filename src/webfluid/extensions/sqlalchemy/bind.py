from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from contextlib import asynccontextmanager, contextmanager


class Bind:
    def __init__(self, key, uris, metadata=None, **engine_kwargs):
        from .model import Model
        sync_uri, async_uri = uris

        self.name = key
        self.metadata = metadata if metadata else Model.metadata_for(key)
        self.sync_engine = create_engine(sync_uri, **engine_kwargs)
        self.async_engine = create_async_engine(async_uri, **engine_kwargs)
        self._sync_session = sessionmaker(self.sync_engine)
        self._async_session = async_sessionmaker(self.async_engine)

    @contextmanager
    def session(self):
        with self._sync_session() as session:
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
        async with self._async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
