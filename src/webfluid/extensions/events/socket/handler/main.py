from fastapi import WebSocketDisconnect
import json

from .subscribe import subscribe
from .unsubscribe import unsubscribe
from .request import request
from .trigger import trigger
from .listen import add_listener


async def _send(ws, response):
    await ws.send_text(json.dumps(response))


class SocketHandler:
    def __init__(self, socket_manager, events, queries):
        self._manager = socket_manager
        self._events = events
        self._queries = queries

    async def _handle(self, ws):
        sid = self._manager.join(ws)
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

                    r = msg["type"]
                    if r == "subscribe":
                        await _send(ws, subscribe(
                            self._manager, self._events,
                            sid, msg, response
                        ))
                        continue

                    elif r == "unsubscribe":
                        await _send(ws, unsubscribe(
                            self._manager, self._events,
                            sid, msg, response
                        ))
                        continue

                    elif r == "request":
                        await _send(ws, await request(
                            self._queries, msg, response
                        ))
                        continue

                    elif r == "trigger":
                        await _send(ws, trigger(
                            self._events, msg, response
                        ))
                        continue

                    elif r == "listen":
                        response = add_listener(
                            self._manager, self._events,
                            sid, msg, response
                        )
                        if response is None: continue

                    else:
                        response["error"] = f"Unknown request: {r}"

                    await _send(ws, response)

        except WebSocketDisconnect: pass
        finally: self._manager.leave(sid)

    async def handle(self, ws):
        await self._handle(ws)
