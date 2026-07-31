from collections.abc import Callable, Iterator
from typing import Any

class Phase:
    name: str
    arity: int
    argument: str | None
    reverse: bool
    closed_after: str | None
    _entries: list[Callable[..., Any]]
    _closed: bool
    def __init__(
        self, name: str, arity: int = 0, argument: str | None = None,
        reverse: bool = False, closed_after: str | None = None
    ) -> None: ...
    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[Callable[..., Any]]: ...
    def _arity_error(self) -> str: ...
    def add(self, fn: Callable[..., Any]) -> Callable[..., Any]: ...
    def seal(self) -> Phase: ...
