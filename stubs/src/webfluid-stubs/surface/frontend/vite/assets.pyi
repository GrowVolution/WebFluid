from collections.abc import Callable, Coroutine, Container
from pathlib import Path
from typing import Any

from fastapi import Request, Response

def contained(root: Path, *parts: str | Path) -> Path | None: ...
def asset_catch(
    project_root: Path, namespaces: Container[str]
) -> Callable[[Request, str], Coroutine[Any, Any, Response]]: ...
