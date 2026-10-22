from contextvars import ContextVar

from webfluid.extensions.sqlalchemy.executor.base import BaseExecutor


class Executor(BaseExecutor):
    _ctx = ContextVar("sqlalchemy.executor")

    def exec(self, statement, scalars=True):
        results = self.session.execute(statement)
        if scalars: return results.scalars()
        return results

    def insert(self, obj, flush=False):
        self.session.add(obj)
        if flush: self.flush()
        return obj

    def delete(self, obj, flush=False):
        self.session.delete(obj)
        if flush: self.flush()

    def flush(self):
        self.session.flush()
