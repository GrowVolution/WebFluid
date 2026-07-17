from collections.abc import Callable
from typing import Any

from webfluid import Fluid

class HookPhase:
    before: bool
    after: bool
    reverse: bool
    _hooks: list[Callable[..., Any]]
    _locked: bool
    def __init__(self, stage: str, reverse: bool = False) -> None: ...
    def add_hook(self, fn: Callable[..., Any]) -> Callable[..., Any]: ...
    async def run_hooks(self, *args: Any) -> None: ...

class Lifecycle:
    before_enable: HookPhase
    after_enable: HookPhase
    def __init__(self) -> None: ...
    async def run_before(self, fluid: Fluid) -> None: ...
    async def run_after(self) -> None: ...
