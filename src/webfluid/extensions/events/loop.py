import json, asyncio

from webfluid.utils.core import safe_execute


class LoopManager:
    def __init__(self, events, socket_manager):
        self._events = events
        self._socket = socket_manager

    def _client_tasks(self, internal, event, data):
        client_tasks = []
        if not self._socket or internal: return client_tasks
        if self._socket.has_subscriptions(event):
            subscriptions = self._socket.get_subscriptions(event)

            for sid in subscriptions:
                ws = self._socket.get_ws(sid)
                if not ws: continue

                for listener_id in self._socket.get_listeners(event, sid):
                    client_tasks.append(ws.send_text(
                        json.dumps({
                            "id": listener_id,
                            "data": data
                        })
                    ))
        return client_tasks

    async def _loop(self, event):
        if not self._events.has_event(event): return
        internal = self._events.is_internal(event)

        async for event_data in self._events.broadcaster(event).stream():
            server_tasks = []
            for fn in self._events.handlers(event):
                server_tasks.append(fn(event, event_data))

            client_tasks = self._client_tasks(internal, event, event_data)

            await asyncio.gather(
                *server_tasks,
                *client_tasks,
                return_exceptions=True
            )

    def create_loop(self, event):
        return asyncio.create_task(safe_execute(
            self._loop, False, event
        ))
