from fastapi import WebSocket
from collections import deque
from uuid import uuid4

from .handler import SocketHandler
from webfluid.core.context import FluidContext


class Subscription:
    __slots__ = ("listeners", "backlog")

    def __init__(self, backlog):
        self.listeners = []
        self.backlog = deque(maxlen=backlog or None)


class SocketManager:
    def __init__(self, fluid, events, queries):
        self._fluid = fluid
        self._handler = SocketHandler(self, events, queries)
        self._backlog = fluid.config["EVENTS_SOCKET_BACKLOG"]
        self._websockets = {}
        self._subscriptions = {}

    async def socket(self, ws: WebSocket):
        await ws.accept()
        async with FluidContext(self._fluid, ws):
            await self._handler.handle(ws)

    def join(self, ws):
        sid = uuid4().hex
        self._websockets[sid] = ws
        return sid

    def get_ws(self, sid):
        return self._websockets.get(sid)

    def leave(self, sid):
        self._websockets.pop(sid, None)
        for event in tuple(self._subscriptions):
            listeners = self._subscriptions[event]
            listeners.pop(sid, None)
            if not listeners: del self._subscriptions[event]

    def has_subscriptions(self, event, sid=None):
        has = event in self._subscriptions
        if sid: return has and sid in self._subscriptions[event]
        return has

    def get_subscriptions(self, event, sid=None):
        if not self.has_subscriptions(event, sid): return None
        if sid: return self._subscriptions[event][sid]
        return self._subscriptions[event]

    def subscribe(self, event, sid):
        if not self.has_subscriptions(event):
            self._subscriptions[event] = {}
        self._subscriptions[event][sid] = Subscription(self._backlog)

    def unsubscribe(self, event, sid):
        if self.has_subscriptions(event):
            self._subscriptions[event].pop(sid, None)

    def add_listener(self, event, sid, msg_id):
        self._subscriptions[event][sid].listeners.append(msg_id)

    def get_listeners(self, event, sid):
        if self.has_subscriptions(event, sid):
            subscription = self._subscriptions[event][sid]
            listeners = subscription.listeners.copy()
            subscription.listeners.clear()
            return listeners
        return []

    def hold(self, event, sid, data):
        if self._backlog and self.has_subscriptions(event, sid):
            self._subscriptions[event][sid].backlog.append(data)

    def take(self, event, sid):
        if not self.has_subscriptions(event, sid): return False, None
        backlog = self._subscriptions[event][sid].backlog
        if not backlog: return False, None
        return True, backlog.popleft()
