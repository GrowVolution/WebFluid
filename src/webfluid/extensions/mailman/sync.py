from threading import Thread
from contextlib import contextmanager
import smtplib

from .context import ClientContext
from .message import make_message
from webfluid.exceptions import FrameworkException


class SyncManager:
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

    def _send_sync(self, msg):
        try:
            ctx = ClientContext.current()
            if ctx.is_async: raise ValueError()
            ctx.client.send_message(msg)
        except (RuntimeError, ValueError):
            with self.client() as smtp:
                smtp.send_message(msg)

    def send(self, to, subject, body, attachments=None,
             from_email=None, cc=None, bcc=None, fake_async=True):

        msg = make_message(
            self.default_sender, to, subject, body,
            attachments, from_email, cc, bcc
        )
        if fake_async: Thread(target=self._send_sync, args=(msg,)).start()
        else: self._send_sync(msg)

    @contextmanager
    def client(self):
        client = smtplib.SMTP_SSL if self.use_tls else smtplib.SMTP
        smtp = None

        try:
            smtp = client(
                host=self.host,
                port=self.port,
                timeout=self.timeout
            )

            if self.start_tls: smtp.starttls()
            if self.user and self.password:
                smtp.login(self.user, self.password)

            with ClientContext(smtp, False): yield smtp
        except (
                smtplib.SMTPConnectError,
                smtplib.SMTPAuthenticationError
        ) as e:
            raise FrameworkException(f"SMTP Connection/Auth failed: {e}")
        except smtplib.SMTPException as e:
            raise FrameworkException(f"Unexpected SMTP error: {type(e).__name__}: {e}")
        finally:
            if smtp is not None:
                try: smtp.quit()
                except: pass
