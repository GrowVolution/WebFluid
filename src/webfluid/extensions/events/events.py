from .broadcast import BroadCaster
from webfluid.utils.core import required_arg_count
from webfluid.exceptions import FrameworkException


class Events:
    def __init__(self, queue_size, ctx_decorator):
        self._event_queue_size = queue_size
        self._ctx_decorator = ctx_decorator
        self._broadcasters = {}
        self._events = {}
        self.create_loop = None

    def _prepare_event(self, name, singleton, internal):
        if singleton and name in self._events:
            raise ValueError(f"Event '{name}' already exists.")

        elif not singleton and self.is_singleton(name):
            raise ValueError(f"Singleton event '{name}' already exists.")

        is_internal = self.is_internal(name)
        if self.has_event(name) and internal != is_internal:
            raise ValueError(f"Event '{name}' is already registered as "
                             f"{'internal' if is_internal else 'public'}.")

        if name not in self._events:
            self._events[name] = {
                "singleton": singleton,
                "internal": internal,
                "handlers": []
            }

        if name not in self._broadcasters:
            self._broadcasters[name] = BroadCaster(
                name, self._event_queue_size
            )
            if callable(self.create_loop):
                self.create_loop(name)

    def create_signal(self, name, singleton=False, internal=False):
        self._prepare_event(name, singleton, internal)

    def event(self, name, singleton=False, internal=True):
        self._prepare_event(name, singleton, internal)

        def decorator(fn):
            if required_arg_count(fn) != 1:
                raise FrameworkException(
                    "Event handlers must receive exactly one argument (data)."
                )
            self._events[name]["handlers"].append(self._ctx_decorator(fn))
            return fn
        return decorator

    def trigger(self, event, data=None):
        if not self.has_event(event):
            raise ValueError(f"Event '{event}' does not exist.")

        self._broadcasters[event].publish(data)

    async def listen(self, event):
        if event not in self._broadcasters:
            raise ValueError(f"Event '{event}' does not exist.")

        async for event_data in self._broadcasters[event].stream():
            yield event_data

    def has_event(self, event):
        return event in self._broadcasters

    def is_singleton(self, event):
        return self.has_event(event) and self._events[event]["singleton"]

    def is_internal(self, event):
        return self.has_event(event) and self._events[event]["internal"]

    def broadcaster(self, event):
        if self.has_event(event):
            return self._broadcasters[event]
        return None

    def handlers(self, event):
        if self.has_event(event):
            return self._events[event]["handlers"]
        return []
