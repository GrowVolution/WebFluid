from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager, AbstractAsyncContextManager
from typing import Any
import smtplib, aiosmtplib

from webfluid import Fluid
from webfluid.extensions.base import FluidExtension
from webfluid.extensions.mailman.sync import SyncManager
from webfluid.extensions.mailman.async_ import AsyncManager


class Mail(FluidExtension):
    _sync: SyncManager | None
    _async: AsyncManager | None
    def __init__(self, fluid: Fluid | None = None) -> None: ...
    def expand_fluid(self, fluid: Fluid, *_: Any, **__: Any) -> None: ...
    def _ensure_initialized(self) -> None: ...
    @property
    def send(self) -> Callable[..., None]: ...
    @property
    def asend(self) -> Callable[..., Awaitable[None]]: ...
    @property
    def client(self) -> Callable[[], AbstractContextManager[smtplib.SMTP]]: ...
    @property
    def async_client(self) -> Callable[[], AbstractAsyncContextManager[aiosmtplib.SMTP]]: ...
