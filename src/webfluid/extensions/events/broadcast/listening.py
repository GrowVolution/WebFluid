from collections import deque
import asyncio


class Listener:
    _last_id = 0
    __slots__ = ("id", "buffer", "event")

    def __init__(self, maxlen):
        self.id = Listener.next_id()
        self.buffer = deque(maxlen=maxlen)
        self.event = asyncio.Event()

    @classmethod
    def next_id(cls):
        cls._last_id += 1
        return cls._last_id
