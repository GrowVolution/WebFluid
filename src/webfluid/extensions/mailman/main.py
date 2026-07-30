from .sync import SyncManager
from .async_ import AsyncManager

from webfluid.extensions.base import FluidExtension
from webfluid.exceptions import FrameworkException


class Mail(FluidExtension):
    def __init__(self, fluid=None):
        self._sync = None
        self._async = None
        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        config = fluid.config

        user = config.get("MAIL_USERNAME")
        password = config.get("MAIL_PASSWORD")
        if user and not password:
            raise FrameworkException("Missing MAIL_PASSWORD for MAIL_USERNAME.")
        if password and not user:
            raise FrameworkException("Missing MAIL_USERNAME for MAIL_PASSWORD.")

        host = config.get("MAIL_SERVER", "localhost")
        port = config.get("MAIL_PORT", 587)
        use_tls = config.get("MAIL_USE_TLS", True)
        start_tls = config.get("MAIL_USE_STARTTLS", False)
        timeout = config.get("MAIL_TIMEOUT", 10)
        default_sender = config.get("MAIL_DEFAULT_SENDER", "noreply@example.com")

        self._sync = SyncManager(
            host, port, use_tls, start_tls, timeout,
            user, password, default_sender
        )
        self._async = AsyncManager(
            host, port, use_tls, start_tls, timeout,
            user, password, default_sender
        )

    def _ensure_initialized(self):
        if not self._sync or not self._async:
            raise FrameworkException("Mail.expand_fluid() has not been called.")

    @property
    def send(self):
        self._ensure_initialized()
        return self._sync.send

    @property
    def asend(self):
        self._ensure_initialized()
        return self._async.send

    @property
    def client(self):
        self._ensure_initialized()
        return self._sync.client

    @property
    def async_client(self):
        self._ensure_initialized()
        return self._async.client
