from contextvars import ContextVar

from webfluid.core.context.base import BaseContext
from webfluid.utils.core import async_result


class AsyncExecutor(BaseContext):
    _ctx = ContextVar("sqlalchemy.async_executor")
    def __init__(self, session):
        self.session = session

    async def exec(self, statement, scalars=True):
        results = await self.session.execute(statement)
        if scalars: return results.scalars()
        return results

    async def insert(self, obj, flush=False):
        self.session.add(obj)
        if flush: await self.flush()
        return obj

    async def delete(self, obj, flush=False):
        await async_result(self.session.delete(obj))
        if flush: await self.flush()

    async def flush(self):
        await self.session.flush()
