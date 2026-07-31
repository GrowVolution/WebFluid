from typing import Any

from webfluid.core.lifecycle.phase import Phase

class Lifecycle:
    before: Phase
    after: Phase
    def __init__(self) -> None: ...
    async def process_before(self) -> Any | None: ...
    async def process_after(self, response: Any) -> Any: ...
