from .listening import Listener
from webfluid.utils.logging import factory as log_factory


class BroadCaster:
    def __init__(self, event, queue_size):
        self.event = event
        self.listeners = set()
        self.queue_size = queue_size

    async def stream(self):
        listener = Listener(self.queue_size or None)
        self.listeners.add(listener)
        try:
            while True:
                while listener.buffer:
                    yield listener.buffer.popleft()
                listener.event.clear()
                if not listener.buffer:
                    await listener.event.wait()
        finally: self.listeners.discard(listener)

    def publish(self, data):
        for listener in self.listeners:
            if self.queue_size and len(listener.buffer) >= self.queue_size:
                dropped = listener.buffer.popleft()
                log_factory.warning(
                    f"Listener {listener.id} of event '{self.event}' is running behind."
                    f"Dropped message: {dropped}"
                )
            listener.buffer.append(data)
            listener.event.set()
