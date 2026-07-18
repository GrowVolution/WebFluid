import asyncio
from collections import deque
from typing import Any

class Listener:
    _last_id: int
    id: int
    buffer: deque[Any]
    event: asyncio.Event
    def __init__(self, maxlen: int | None) -> None: ...
    @classmethod
    def next_id(cls) -> int: ...
