from .events import Events
from .queries import Queries
from .loop import LoopManager
from .socket import SocketManager

from webfluid.extensions.base import FluidExtension
from webfluid.core.constants import WF_STATIC
from webfluid.core.context import FluidContext
from webfluid.utils import safe_execute
from webfluid.exceptions import FrameworkException


class EventManager(FluidExtension):
    def __init__(self, fluid=None):
        self._events = None
        self._queries = None
        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        def ctx_decorator(fn):
            async def ctx_wrapper(event, data):
                try: parent = FluidContext.current()
                except RuntimeError: parent = None
                async with FluidContext(
                        fluid, parent.request if parent is not None else None,
                        event=event, event_data=data
                ) as ctx:
                    return await safe_execute(fn, ctx.request is not None, data)
            return ctx_wrapper

        self._events = Events(fluid.config.get(
            "EVENTS_EVENT_QUEUE_SIZE", 5
        ), ctx_decorator)
        self._queries = Queries(ctx_decorator)

        socket_manager = None
        if fluid.config.get("EVENTS_CONFIGURE_SOCKET", True):
            socket_manager = SocketManager(self._events, self._queries)
            fluid.websocket("/ws/events")(socket_manager.socket)
            fluid.add_source(
                f'<script src="{WF_STATIC}/js/events.js" type="module"></script>',
                priority=5
            )

        loop_manager = LoopManager(self._events, socket_manager)
        self._events.create_loop = loop_manager.create_loop

    def _ensure_initialized(self):
        if not self._events or not self._queries:
            raise FrameworkException("EventManager.expand_fluid() has not been called.")

    @property
    def create_signal(self):
        self._ensure_initialized()
        return self._events.create_signal

    @property
    def event(self):
        self._ensure_initialized()
        return self._events.event

    @property
    def trigger(self):
        self._ensure_initialized()
        return self._events.trigger

    @property
    def listen(self):
        self._ensure_initialized()
        return self._events.listen

    @property
    def query(self):
        self._ensure_initialized()
        return self._queries.query

    @property
    def request(self):
        self._ensure_initialized()
        return self._queries.request
