from collections.abc import Callable
from typing import Any

from webfluid.core.lifecycle.phase import Phase

class JinjaContext:
    _processors: Phase
    def __init__(self) -> None: ...
    def add_processor(self, fn: Callable[..., Any]) -> Callable[..., Any]: ...
    async def process(self, ctx: dict[str, Any]) -> dict[str, Any]: ...
