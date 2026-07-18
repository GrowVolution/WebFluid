from collections.abc import AsyncGenerator
from typing import Any

from webfluid.extensions.events.broadcast.listening import Listener

class BroadCaster:
    event: str
    listeners: set[Listener]
    queue_size: int
    def __init__(self, event: str, queue_size: int) -> None: ...
    def stream(self) -> AsyncGenerator[Any]: ...
    def publish(self, data: Any) -> None: ...
