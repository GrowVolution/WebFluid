from collections.abc import Callable
from typing import Any

from webfluid import Fluid
from webfluid.extensions.base import FluidExtension
from webfluid.extensions.mailman.async_ import AsyncManager
from webfluid.extensions.mailman.sync import SyncManager

class Mail(FluidExtension):
    _sync: SyncManager | None
    _async: AsyncManager | None
    send: Callable[..., None]
    asend: Callable[..., Any]
    client: Callable[..., Any]
    async_client: Callable[..., Any]
    def __init__(self, fluid: Fluid | None = None) -> None: ...
    def expand_fluid(self, fluid: Fluid, *args: Any, **kwargs: Any) -> None: ...
