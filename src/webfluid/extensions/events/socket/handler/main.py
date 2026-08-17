from fastapi import WebSocketDisconnect
import json

from .subscribe import subscribe
from .unsubscribe import unsubscribe
from .request import request
from .trigger import trigger
from .listen import add_listener

from webfluid.utils.logging import factory as log_factory

_KEYS = ("id", "type", "data")


async def _send(ws, response):
    await ws.send_text(json.dumps(response))


async def _receive(ws):
    try: raw = await ws.receive_text()
    except KeyError: return None, "only text frames are supported"

    try: msg = json.loads(raw)
    except json.JSONDecodeError: return None, "invalid json"

    if not isinstance(msg, dict): return None, "message must be an object"

    for key in _KEYS:
        if key not in msg: return None, f"missing '{key}' in message"

    return msg, None


class SocketHandler:
    def __init__(self, socket_manager, events, queries):
        self._manager = socket_manager
        self._events = events
        self._queries = queries

    async def _dispatch(self, ws, sid, msg):
        response = { "id": msg["id"] }

        r = msg["type"]
        if r == "subscribe":
            return await _send(ws, subscribe(
                self._manager, self._events,
                sid, msg, response
            ))

        elif r == "unsubscribe":
            return await _send(ws, unsubscribe(
                self._manager, self._events,
                sid, msg, response
            ))

        elif r == "request":
            return await _send(ws, await request(
                self._queries, msg, response
            ))

        elif r == "trigger":
            return await _send(ws, trigger(
                self._events, msg, response
            ))

        elif r == "listen":
            response = add_listener(
                self._manager, self._events,
                sid, msg, response
            )
            if response is None: return None

        else:
            response["error"] = f"Unknown request: {r}"

        await _send(ws, response)

    async def _handle(self, ws):
        sid = self._manager.join(ws)
        try:
            while True:
                msg, error = await _receive(ws)
                if msg is None:
                    await _send(ws, { "error": error })
                    continue

                try: await self._dispatch(ws, sid, msg)
                except WebSocketDisconnect: raise
                except Exception as e:
                    log_factory.exception(e)
                    await _send(ws, {
                        "id": msg["id"],
                        "error": f"Request '{msg['type']}' failed."
                    })

        except WebSocketDisconnect: pass
        finally: self._manager.leave(sid)

    async def handle(self, ws):
        await self._handle(ws)
