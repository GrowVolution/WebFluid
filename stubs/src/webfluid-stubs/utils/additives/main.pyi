from collections.abc import Callable
from typing import Any

from webfluid import Fluid

def require_extensions(
    *extensions: str
) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
async def register_additives(fluid: Fluid) -> None: ...
