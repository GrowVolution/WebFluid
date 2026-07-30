from contextvars import ContextVar
from typing import Any
import smtplib, aiosmtplib

from webfluid.core.context.base import BaseContext


class ClientContext(BaseContext):
    _ctx: ContextVar[Any]
    client: smtplib.SMTP | aiosmtplib.SMTP
    is_async: bool
    def __init__(
        self, client: smtplib.SMTP | aiosmtplib.SMTP,
        is_async: bool
    ) -> None: ...
