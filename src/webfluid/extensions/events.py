from fastapi import WebSocket
from markupsafe import Markup
from uuid import uuid4
from typing import TYPE_CHECKING, Callable, Optional, Any
import asyncio, json

from webfluid.extensions.base import FluidExtension
from webfluid.core.constants import WF_STATIC
from webfluid.utils import required_arg_count, safe_execute
from webfluid.exceptions import FrameworkException

if TYPE_CHECKING:
    from webfluid.core.fluid import Fluid


class _BroadCaster:
    def __init__(self, queue_size: int):
        self.listeners = set()
        self.queue_size = queue_size

    async def stream(self):
        queue = asyncio.Queue(self.queue_size)
        self.listeners.add(queue)
        try:
            while True:
                yield await queue.get()
                queue.task_done()
        finally: self.listeners.remove(queue)

    def publish(self, data: Any):
        dead = []

        for queue in list(self.listeners):
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(data)
                except asyncio.QueueEmpty:
                    dead.append(queue)

        for q in dead:
            self.listeners.discard(q)


class EventManager(FluidExtension):
    def __init__(self, fluid: "Fluid | None" = None):
        self._broadcasters = {}
        self._events = {}
        self._queries = {}
        self._websockets = {}
        self._subscriptions = {}
        self._event_queue_size = 5
        super().__init__(fluid)

    def expand_fluid(self, fluid: "Fluid", *_, **__):
        self._event_queue_size = fluid.config.get(
            "EVENTS_EVENT_QUEUE_SIZE", self._event_queue_size
        )

        fluid.websocket("/ws/events")(self._socket_manager)
        fluid.sources.append(
            Markup(f'<script src="{WF_STATIC}/js/events.js" type="module"></script>')
        )

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

                    elif request == "listen":
                        event = msg["data"]
                        if event not in self._events or event not in self._subscriptions:
                            response["error"] = f"Event '{event}' does not exist or was not subscribed to."
                            await ws.send_text(json.dumps(response))
                            continue

                        self._subscriptions[event][sid] = msg["id"]
                        continue

                    elif request == "query":
                        data = msg["data"]
                        if not isinstance(data, dict):
                            response["error"] = "Request data must be a dict."
                            await ws.send_text(json.dumps(response))
                            continue

                        query = data.get("query")
                        if query not in self._queries:
                            response["error"] = f"Query '{query}' does not exist."
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
                            await ws.send_text(json.dumps(response))
                            continue

                        await self.trigger(event, data.get("data"))
                        response["data"] = True

                    else:
                        response["error"] = f"Unknown request: {request}"

                    await ws.send_text(json.dumps(response))

        finally: self._websockets.pop(sid, None)

    async def _event_loop(self, event: str):
        if event not in self._broadcasters: return

        async for event_data in self._broadcasters[event].stream():
            server_tasks = []
            for fn in self._events[event]:
                server_tasks.append(safe_execute(
                    fn, False,
                    event_data
                ))

            client_tasks = []
            if event in self._subscriptions:
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

    def event(self, name: str) -> Callable:
        if name not in self._broadcasters:
            self._broadcasters[name] = _BroadCaster(
                self._event_queue_size
            )
            asyncio.create_task(safe_execute(
                self._event_loop, False, name
            ))

        if name not in self._events:
            self._events[name] = []

        def decorator(fn):
            if required_arg_count(fn) != 1:
                raise FrameworkException("Event handlers must receive exactly one argument (data).")
            self._events[name].append(fn)
            return fn
        return decorator

    def query(self, name: str) -> Callable:
        if name in self._queries:
            raise ValueError(f"Query '{name}' already exists.")

        def decorator(fn):
            if required_arg_count(fn) != 1:
                raise FrameworkException("Query handlers must receive exactly one argument (data).")
            self._queries[name] = fn
            return fn
        return decorator

    async def trigger(self, event: str, data: Optional[Any] = None):
        if event not in self._broadcasters:
            raise ValueError(f"Event '{event}' does not exist.")

        await self._broadcasters[event].publish(data)

    async def listen(self, event: str):
        if event not in self._broadcasters:
            raise ValueError(f"Event '{event}' does not exist.")

        async for event_data in self._broadcasters[event].stream():
            yield event_data

    async def request(self, query: str, data: Optional[Any] = None):
        if query not in self._queries:
            raise ValueError(f"Query '{query}' does not exist.")

        query_fn = self._queries[query]
        return await safe_execute(query_fn, True, data)
