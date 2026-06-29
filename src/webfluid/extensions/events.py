from fastapi import WebSocket
from uuid import uuid4
from collections import deque
from typing import TYPE_CHECKING, Callable, Optional, Any, AsyncGenerator
import asyncio, json

from webfluid.extensions.base import FluidExtension
from webfluid.core.constants import WF_STATIC
from webfluid.core.context import FluidContext
from webfluid.utils import required_arg_count, safe_execute
from webfluid.exceptions import FrameworkException

if TYPE_CHECKING:
    from webfluid import Fluid


class _Listener:
    __slots__ = ("buffer", "event")

    def __init__(self, maxlen: Optional[int]):
        self.buffer = deque(maxlen=maxlen)
        self.event = asyncio.Event()


class _BroadCaster:
    def __init__(self, queue_size: int):
        self.listeners = set()
        self.queue_size = queue_size

    async def stream(self):
        listener = _Listener(self.queue_size or None)
        self.listeners.add(listener)
        try:
            while True:
                while listener.buffer:
                    yield listener.buffer.popleft()
                listener.event.clear()
                if not listener.buffer:
                    await listener.event.wait()
        finally: self.listeners.discard(listener)

    def publish(self, data: Any):
        for listener in self.listeners:
            listener.buffer.append(data)
            listener.event.set()


class EventManager(FluidExtension):
    def __init__(self, fluid: Optional["Fluid"] = None):
        self._broadcasters = {}
        self._events = {}
        self._queries = {}
        self._websockets = {}
        self._subscriptions = {}
        self._event_queue_size = 5
        self._ctx_decorator = None
        super().__init__(fluid)

    def expand_fluid(self, fluid: "Fluid", *_, **__):
        self._event_queue_size = fluid.config.get(
            "EVENTS_EVENT_QUEUE_SIZE", self._event_queue_size
        )

        if fluid.config.get("EVENTS_CONFIGURE_SOCKET", True):
            fluid.websocket("/ws/events")(self._socket_manager)
            fluid.add_source(
                f'<script src="{WF_STATIC}/js/events.js" type="module"></script>',
                priority=5
            )

        def ctx_decorator(fn):
            async def ctx_wrapper(event: str, data: Any):
                try: parent = FluidContext.current()
                except RuntimeError: parent = None
                async with FluidContext(
                    fluid, parent.request if parent is not None else None,
                    event=event, event_data=data
                ):
                    return await safe_execute(fn, False, data)
            return ctx_wrapper

        self._ctx_decorator = ctx_decorator

    async def _socket_manager(self, ws: WebSocket):
        await ws.accept()

        sid = uuid4().hex
        self._websockets[sid] = ws

        try:
            while True:
                try:
                    msg = json.loads(await ws.receive_text())
                except json.JSONDecodeError:
                    await ws.send_text(json.dumps({"error": "invalid json"}))
                    continue

                for key in {"id", "type", "data"}:
                    if key not in msg:
                        await ws.send_text(json.dumps({"error": f"missing '{key}' in message"}))
                        break
                else:
                    response = {
                        "id": msg["id"]
                    }

                    request = msg["type"]
                    if request == "subscribe":
                        event = msg["data"]
                        if event not in self._events:
                            response["error"] = f"Event '{msg['data']}' does not exist."

                        elif self._events[event]["internal"]:
                            response["error"] = f"Event '{msg['data']}' is not public."

                        if "error" in response:
                            await ws.send_text(json.dumps(response))
                            continue

                        if event not in self._subscriptions:
                            self._subscriptions[event] = {}

                        self._subscriptions[event][sid] = None
                        response["data"] = True

                    elif request == "unsubscribe":
                        event = msg["data"]
                        if event not in self._events or event not in self._subscriptions:
                            response["error"] = f"Event '{event}' does not exist or was not subscribed to."
                            await ws.send_text(json.dumps(response))
                            continue

                        self._subscriptions[event].pop(sid, None)
                        response["data"] = True

                    elif request == "request":
                        data = msg["data"]
                        if not isinstance(data, dict):
                            response["error"] = "Request data must be a dict."
                            await ws.send_text(json.dumps(response))
                            continue

                        query = data.get("query")
                        if query not in self._queries:
                            response["error"] = f"Query '{query}' does not exist."

                        elif self._queries[query]["internal"]:
                            response["error"] = f"Query '{query}' is not public."

                        if "error" in response:
                            await ws.send_text(json.dumps(response))
                            continue

                        response["data"] = await self.request(query, data.get("data"))

                    elif request == "trigger":
                        data = msg["data"]
                        if not isinstance(data, dict):
                            response["error"] = "Request data must be a dict."
                            await ws.send_text(json.dumps(response))
                            continue

                        event = data.get("event")
                        if not event:
                            response["error"] = "Request data must contain an 'event' key."
                            await ws.send_text(json.dumps(response))
                            continue

                        if event not in self._events:
                            response["error"] = f"Event '{event}' does not exist."

                        elif self._events[event]["internal"]:
                            response["error"] = f"Event '{event}' is not public."

                        if "error" in response:
                            await ws.send_text(json.dumps(response))
                            continue

                        self.trigger(event, data.get("data"))
                        response["data"] = True

                    elif request == "listen":
                        event = msg["data"]
                        if event not in self._events or event not in self._subscriptions:
                            response["error"] = f"Event '{event}' does not exist or was not subscribed to."
                            await ws.send_text(json.dumps(response))
                            continue

                        self._subscriptions[event][sid] = msg["id"]
                        continue

                    else:
                        response["error"] = f"Unknown request: {request}"

                    await ws.send_text(json.dumps(response))

        finally: self._websockets.pop(sid, None)

    async def _event_loop(self, event: str):
        if event not in self._broadcasters: return
        not_internal = not self._events[event]["internal"]

        async for event_data in self._broadcasters[event].stream():
            server_tasks = []
            for fn in self._events[event]["handlers"]:
                server_tasks.append(fn(event, event_data))

            client_tasks = []
            if not_internal and event in self._subscriptions:
                subscriptions = self._subscriptions[event].copy()

                for sid, listener_id in subscriptions.items():
                    if not listener_id: continue

                    ws = self._websockets.get(sid)
                    if not ws: continue

                    client_tasks.append(ws.send_text(
                        json.dumps({
                            "id": listener_id,
                            "data": event_data
                        })
                    ))

                    self._subscriptions[event][sid] = None

            await asyncio.gather(
                *server_tasks,
                *client_tasks,
                return_exceptions=True
            )

    def _prepare_event(self, name: str, singleton: bool, internal: bool):
        if singleton and name in self._events:
            raise ValueError(f"Event '{name}' already exists.")

        elif not singleton and name in self._events and self._events[name]["singleton"]:
            raise ValueError(f"Singleton event '{name}' already exists.")

        if name in self._events and internal != self._events[name]["internal"]:
            raise ValueError(f"Event '{name}' is already registered as "
                             f"{'internal' if self._events[name]['internal'] else 'public'}.")

        if name not in self._events:
            self._events[name] = {
                "singleton": singleton,
                "internal": internal,
                "handlers": []
            }

        if name not in self._broadcasters:
            self._broadcasters[name] = _BroadCaster(
                self._event_queue_size
            )
            asyncio.create_task(safe_execute(
                self._event_loop, False, name
            ))

    def create_signal(self, name: str, singleton: bool = False, internal: bool = False):
        self._prepare_event(name, singleton, internal)

    def event(self, name: str, singleton: bool = False, internal: bool = True) -> Callable:
        if not self._ctx_decorator:
            raise FrameworkException("EventManager.expand_fluid() must be called before registering events.")

        self._prepare_event(name, singleton, internal)

        def decorator(fn):
            if required_arg_count(fn) != 1:
                raise FrameworkException("Event handlers must receive exactly one argument (data).")
            self._events[name]["handlers"].append(self._ctx_decorator(fn))
            return fn
        return decorator

    def query(self, name: str, singleton: bool = True, internal: bool = True) -> Callable:
        if not self._ctx_decorator:
            raise FrameworkException("EventManager.expand_fluid() must be called before registering queries.")

        if singleton and name in self._queries:
            raise ValueError(f"Query '{name}' already exists.")

        elif not singleton and name in self._queries and self._queries[name]["singleton"]:
            raise ValueError(f"Singleton query '{name}' already exists.")

        if name not in self._queries:
            self._queries[name] = {
                "singleton": singleton,
                "internal": internal,
                "handlers": []
            }

        def decorator(fn):
            if required_arg_count(fn) != 1:
                raise FrameworkException("Query handlers must receive exactly one argument (data).")
            self._queries[name]["handlers"].append(self._ctx_decorator(fn))
            return fn
        return decorator

    def trigger(self, event: str, data: Optional[Any] = None):
        if event not in self._broadcasters:
            raise ValueError(f"Event '{event}' does not exist.")

        self._broadcasters[event].publish(data)

    async def listen(self, event: str) -> AsyncGenerator[Optional[Any]]:
        if event not in self._broadcasters:
            raise ValueError(f"Event '{event}' does not exist.")

        async for event_data in self._broadcasters[event].stream():
            yield event_data

    async def request(self, query: str, data: Optional[Any] = None) -> Any | list[Any]:
        if query not in self._queries:
            raise ValueError(f"Query '{query}' does not exist.")

        tasks = [
            safe_execute(fn, True, query, data)
            for fn in self._queries[query]["handlers"]
        ]
        results = await asyncio.gather(*tasks)
        return results[0] if self._queries[query]["singleton"] else results
