from fastapi import WebSocket
from uuid import uuid4

from .handler import SocketHandler


class SocketManager:
    def __init__(self, events, queries):
        self._handler = SocketHandler(self, events, queries)
        self._websockets = {}
        self._subscriptions = {}

    async def socket(self, ws: WebSocket):
        await ws.accept()
        await self._handler.handle(ws)

    def join(self, ws):
        sid = uuid4().hex
        self._websockets[sid] = ws
        return sid

    def get_ws(self, sid):
        return self._websockets.get(sid)

    def leave(self, sid):
        self._websockets.pop(sid, None)

    def has_subscriptions(self, event, sid=None):
        has = event in self._subscriptions
        if sid: return has and sid in self._subscriptions[event]
        return has

    def get_subscriptions(self, event, sid=None):
        if not self.has_subscriptions(event, sid): return None
        if sid: return self._subscriptions[event].get(sid, [])
        return self._subscriptions[event]

    def subscribe(self, event, sid):
        if not self.has_subscriptions(event):
            self._subscriptions[event] = {}
        self._subscriptions[event][sid] = []

    def unsubscribe(self, event, sid):
        if self.has_subscriptions(event):
            self._subscriptions[event].pop(sid, None)

    def add_listener(self, event, sid, msg_id):
        self._subscriptions[event][sid].append(msg_id)

    def get_listeners(self, event, sid):
        if self.has_subscriptions(event, sid):
            listeners = self._subscriptions[event][sid].copy()
            self._subscriptions[event][sid].clear()
            return listeners
        return []
