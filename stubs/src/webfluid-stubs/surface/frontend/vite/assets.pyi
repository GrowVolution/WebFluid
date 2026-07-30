from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from fastapi import Request, Response

def asset_catch(
    project_root: Path
) -> Callable[[Request, str], Coroutine[Any, Any, Response]]: ...
