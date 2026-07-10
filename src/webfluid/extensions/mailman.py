from contextlib import contextmanager, asynccontextmanager
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from contextvars import ContextVar
from threading import Thread
import aiosmtplib, smtplib

from webfluid.core.context import BaseContext
from webfluid.extensions.base import FluidExtension
from webfluid.exceptions import FrameworkException


class _ClientContext(BaseContext):
    _ctx = ContextVar("mailman.client")

    def __init__(self, client, is_async):
        self.client = client
        self.is_async = is_async


class Mail(FluidExtension):
    def __init__(self, fluid=None):
        self.host = "localhost"
        self.port = 587
        self.use_tls = True
        self.start_tls = False
        self.timeout = 10

        self.user = None
        self.password = None
        self.default_sender = "noreply@example.com"

        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        config = fluid.config

        self.user = config.get("MAIL_USERNAME")
        self.password = config.get("MAIL_PASSWORD")
        if self.user and not self.password:
            raise FrameworkException("Missing MAIL_PASSWORD for MAIL_USERNAME.")
        if self.password and not self.user:
            raise FrameworkException("Missing MAIL_USERNAME for MAIL_PASSWORD.")

        self.host = config.get("MAIL_SERVER", self.host)
        self.port = config.get("MAIL_PORT", self.port)
        self.use_tls = config.get("MAIL_USE_TLS", self.use_tls)
        self.start_tls = config.get("MAIL_USE_STARTTLS", self.start_tls)
        self.timeout = config.get("MAIL_TIMEOUT", self.timeout)

        self.default_sender = config.get("MAIL_DEFAULT_SENDER", self.default_sender)

    def make_message(self, to, subject, body, attachments=None,
                     from_email=None, cc=None, bcc=None):
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = from_email or self.default_sender
            msg["To"] = to
            if cc: msg["Cc"] = ", ".join(cc)
            if bcc: msg["Bcc"] = ", ".join(bcc)
            msg["Subject"] = subject

            for t, content in body.items():
                msg.attach(MIMEText(content, t, "utf-8"))

            if attachments:
                for attachment in attachments:
                    data = attachment["bytes"]
                    data = data if isinstance(data, bytes) else data.encode("utf-8")
                    application = MIMEApplication(
                        data, attachment["type"]
                    )
                    application.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=attachment["filename"]
                    )
                    msg.attach(application)
        except KeyError as e:
            raise FrameworkException(f"Failed to send async mail: {e}")

        return msg

    def _send_sync(self, msg):
        try:
            ctx = _ClientContext.current()
            if ctx.is_async: raise ValueError()
            ctx.client.send_message(msg)
        except (RuntimeError, ValueError):
            with self.client() as smtp:
                smtp.send_message(msg)

    def send(self, to, subject, body, attachments=None,
             from_email=None, cc=None, bcc=None, fake_async=True):

        msg = self.make_message(to, subject, body, attachments, from_email, cc, bcc)
        if fake_async: Thread(target=self._send_sync, args=(msg,)).start()
        else: self._send_sync(msg)

    async def send_async(self, to, subject, body, attachments=None,
                         from_email=None, cc=None, bcc=None):

        msg = self.make_message(to, subject, body, attachments, from_email, cc, bcc)
        try:
            ctx = _ClientContext.current()
            if not ctx.is_async: raise ValueError()
            await ctx.client.send_message(msg)
        except (RuntimeError, ValueError):
            async with self.async_client() as smtp:
                await smtp.send_message(msg)

    @contextmanager
    def client(self):
        smtp = smtplib.SMTP(
            host=self.host,
            port=self.port,
            timeout=self.timeout
        )

        if self.start_tls: smtp.starttls()
        if self.user and self.password:
            smtp.login(self.user, self.password)

        try:
            with _ClientContext(smtp, False): yield smtp
        except (
            smtplib.SMTPConnectError,
            smtplib.SMTPAuthenticationError
        ) as e:
            raise FrameworkException(f"SMTP Connection/Auth failed: {e}")
        except smtplib.SMTPException as e:
            raise FrameworkException(f"Unexpected SMTP error: {type(e).__name__}: {e}")
        finally:
            try: smtp.quit()
            except: pass

    @asynccontextmanager
    async def async_client(self):
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
            with _ClientContext(smtp, True): yield smtp
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
