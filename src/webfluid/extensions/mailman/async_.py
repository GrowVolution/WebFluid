from contextlib import asynccontextmanager
import aiosmtplib

from .context import ClientContext
from .message import make_message
from webfluid.exceptions import FrameworkException


class AsyncManager:
    def __init__(
            self, host, port,
            use_tls, start_tls, timeout,
            user, password, default_sender
    ):
        self.host = host
        self.port = port
        self.use_tls = use_tls
        self.start_tls = start_tls
        self.timeout = timeout
        self.user = user
        self.password = password
        self.default_sender = default_sender

    async def send(self, to, subject, body, attachments=None,
                         from_email=None, cc=None, bcc=None):

        msg = make_message(
            self.default_sender, to, subject, body,
            attachments, from_email, cc, bcc
        )
        try:
            ctx = ClientContext.current()
            if not ctx.is_async: raise ValueError()
            await ctx.client.send_message(msg)
        except (RuntimeError, ValueError):
            async with self.client() as smtp:
                await smtp.send_message(msg)

    @asynccontextmanager
    async def client(self):
        smtp = aiosmtplib.SMTP(
            hostname=self.host,
            port=self.port,
            use_tls=self.use_tls,
            start_tls=self.start_tls,
            timeout=self.timeout
        )

        await smtp.connect()
        if self.user and self.password:
            await smtp.login(self.user, self.password)

        try:
            with ClientContext(smtp, True): yield smtp
        except (
                aiosmtplib.SMTPConnectError,
                aiosmtplib.SMTPConnectTimeoutError,
                aiosmtplib.SMTPAuthenticationError,
        ) as e:
            raise FrameworkException(f"SMTP Connection/Auth failed: {e}")
        except aiosmtplib.SMTPException as e:
            raise FrameworkException(f"Unexpected SMTP error: {type(e).__name__}: {e}")
        finally:
            try: await smtp.quit()
            except: pass
