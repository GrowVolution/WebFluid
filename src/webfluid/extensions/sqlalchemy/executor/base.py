from abc import ABC, abstractmethod

from webfluid.core.context.base import BaseContext


class BaseExecutor(ABC, BaseContext):
    def __init__(self, session, bind_key=None):
        self.session = session
        self._bind_key = bind_key

    def _accepts_bind(self, bind_key, model):
        if self._bind_key is None or not (bind_key or model): return True
        return self._bind_key == (bind_key or getattr(model, "__bind_key__", "default"))

    @abstractmethod
    def exec(self, statement, scalars=True): ...

    @abstractmethod
    def insert(self, obj, flush=False): ...

    @abstractmethod
    def delete(self, obj, flush=False): ...

    @abstractmethod
    def flush(self): ...
