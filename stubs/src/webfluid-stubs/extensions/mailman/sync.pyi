from collections.abc import Iterator
from contextlib import contextmanager
from email.mime.multipart import MIMEMultipart
import smtplib


class SyncManager:
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
    def _send_sync(self, msg: MIMEMultipart) -> None: ...
    def send(
        self, to: str, subject: str, body: dict[str, str],
        attachments: list[dict[str, bytes | str]] | None = None,
        from_email: str | None = None, cc: list[str] | None = None,
        bcc: list[str] | None = None, fake_async: bool = True
    ) -> None: ...
    @contextmanager
    def client(self) -> Iterator[smtplib.SMTP]: ...
