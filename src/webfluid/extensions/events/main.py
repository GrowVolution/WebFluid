from .events import Events
from .queries import Queries
from .loop import LoopManager
from .socket import SocketManager

from webfluid.extensions.base import Delegated, FluidExtension
from webfluid.core.constants import WF_STATIC
from webfluid.core.context import FluidContext
from webfluid.utils.core import safe_execute


def _context_decorator(fluid):
    def decorator(fn):
        async def wrapper(event, data):
            parent = FluidContext.try_current()
            async with FluidContext(
                    fluid, parent.request if parent is not None else None,
                    event=event, event_data=data
            ) as ctx:
                return await safe_execute(fn, ctx.request is not None, data)
        return wrapper
    return decorator


class EventManager(FluidExtension):
    create_signal = Delegated("_events.create_signal")
    event = Delegated("_events.event")
    trigger = Delegated("_events.trigger")
    listen = Delegated("_events.listen")
    query = Delegated("_queries.query")
    request = Delegated("_queries.request")

    def __init__(self, fluid=None):
        self._events = None
        self._queries = None
        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        decorator = _context_decorator(fluid)

        self._events = Events(fluid.config["EVENTS_EVENT_QUEUE_SIZE"], decorator)
        self._queries = Queries(decorator)

        socket_manager = None
        if fluid.config["EVENTS_CONFIGURE_SOCKET"]:
            socket_manager = SocketManager(self._events, self._queries)
            fluid.websocket("/ws/events")(socket_manager.socket)
            fluid.add_source(
                f'<script src="{WF_STATIC}/js/events.js" type="module"></script>',
                priority=5
            )

        loop_manager = LoopManager(self._events, socket_manager)
        self._events.create_loop = loop_manager.create_loop
