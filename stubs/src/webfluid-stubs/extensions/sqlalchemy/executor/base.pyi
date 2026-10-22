from abc import ABC, abstractmethod
from typing import Any

from webfluid.core.context.base import BaseContext


class BaseExecutor(ABC, BaseContext):
    session: Any
    def __init__(self, session: Any) -> None: ...
    @abstractmethod
    def exec(self, statement: Any, scalars: bool = True) -> Any: ...
    @abstractmethod
    def insert(self, obj: Any, flush: bool = False) -> Any: ...
    @abstractmethod
    def delete(self, obj: Any, flush: bool = False) -> Any: ...
    @abstractmethod
    def flush(self) -> Any: ...
