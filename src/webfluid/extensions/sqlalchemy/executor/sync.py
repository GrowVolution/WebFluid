from contextvars import ContextVar

from webfluid.core.context.base import BaseContext


class Executor(BaseContext):
    _ctx = ContextVar("sqlalchemy.executor")
    def __init__(self, session):
        self.session = session

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
