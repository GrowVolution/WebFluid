from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from email.mime.multipart import MIMEMultipart
from contextvars import ContextVar
from typing import Any
import smtplib, aiosmtplib

from webfluid import Fluid
from webfluid.core.context import BaseContext
from webfluid.extensions.base import FluidExtension


class _ClientContext(BaseContext):
    _ctx: ContextVar[Any]
    def __init__(
        self, client: smtplib.SMTP | aiosmtplib.SMTP,
        is_async: bool
    ) -> None: ...


class Mail(FluidExtension):
    host: str
    port: int
    use_tls: bool
    start_tls: bool
    timeout: int
    user: str | None
    password: str | None
    default_sender: str
    def __init__(self, fluid: Fluid | None = None) -> None: ...
    def expand_fluid(self, fluid: Fluid, *_: Any, **__: Any) -> None: ...
    def make_message(
        self, to: str, subject: str, body: dict[str, str],
        attachments: list[dict[str, bytes | str]] | None = None,
        from_email: str | None = None, cc: list[str] | None = None,
        bcc: list[str] | None = None
    ) -> MIMEMultipart: ...
    def _send_sync(self, msg: MIMEMultipart) -> None: ...
    def send(
        self, to: str, subject: str, body: dict[str, str],
        attachments: list[dict[str, bytes | str]] | None = None,
        from_email: str | None = None, cc: list[str] | None = None,
        bcc: list[str] | None = None, fake_async: bool = True
    ) -> None: ...
    async def send_async(
        self, to: str, subject: str, body: dict[str, str],
        attachments: list[dict[str, bytes | str]] | None = None,
        from_email: str | None = None, cc: list[str] | None = None,
        bcc: list[str] | None = None
    ) -> None: ...
    @contextmanager
    def client(self) -> Iterator[smtplib.SMTP]: ...
    @asynccontextmanager
    def async_client(self) -> AsyncIterator[aiosmtplib.SMTP]: ...
