from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import aiosmtplib


class AsyncManager:
    host: str
    port: int
    use_tls: bool
    start_tls: bool
    timeout: int
    user: str | None
    password: str | None
    default_sender: str
    def __init__(
        self, host: str, port: int,
        use_tls: bool, start_tls: bool, timeout: int,
        user: str | None, password: str | None, default_sender: str
    ) -> None: ...
    async def send(
        self, to: str, subject: str, body: dict[str, str],
        attachments: list[dict[str, bytes | str]] | None = None,
        from_email: str | None = None, cc: list[str] | None = None,
        bcc: list[str] | None = None
    ) -> None: ...
    @asynccontextmanager
    def client(self) -> AsyncIterator[aiosmtplib.SMTP]: ...
