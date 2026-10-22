from abc import ABC, abstractmethod

from webfluid.core.context.base import BaseContext


class BaseExecutor(ABC, BaseContext):
    def __init__(self, session):
        self.session = session

    @abstractmethod
    def exec(self, statement, scalars=True): ...

    @abstractmethod
    def insert(self, obj, flush=False): ...

    @abstractmethod
    def delete(self, obj, flush=False): ...

    @abstractmethod
    def flush(self): ...
