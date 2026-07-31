from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from webfluid import Fluid
from webfluid.extensions.base import FluidExtension
from webfluid.extensions.events.events import Events
from webfluid.extensions.events.queries import Queries

def _context_decorator(fluid: Fluid) -> Callable[..., Any]: ...

class EventManager(FluidExtension):
    _events: Events | None
    _queries: Queries | None
    create_signal: Callable[..., None]
    event: Callable[..., Callable[..., Any]]
    trigger: Callable[..., None]
    listen: Callable[[str], AsyncIterator[Any]]
    query: Callable[..., Callable[..., Any]]
    request: Callable[..., Awaitable[Any]]
    def __init__(self, fluid: Fluid | None = None) -> None: ...
    def expand_fluid(self, fluid: Fluid, *args: Any, **kwargs: Any) -> None: ...
