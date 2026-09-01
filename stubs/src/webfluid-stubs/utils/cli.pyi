from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from webfluid.core.context import BaseContext

class CliContext(BaseContext):
    _ctx: ContextVar[CliContext]
    bar: Any
    def __init__(self, bar: Any) -> None: ...
    @classmethod
    def current(cls) -> CliContext: ...
    @classmethod
    def try_current(cls) -> CliContext | None: ...

@contextmanager
def progress_bar(
    description: str, length: int | None, **kwargs: Any
) -> Iterator[Any]: ...
def download_file(url: str, dest: Path) -> None: ...
