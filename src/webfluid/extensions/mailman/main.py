from .sync import SyncManager
from .async_ import AsyncManager

from webfluid.extensions.base import Delegated, FluidExtension
from webfluid.exceptions import FrameworkException


class Mail(FluidExtension):
    send = Delegated("_sync.send")
    client = Delegated("_sync.client")
    asend = Delegated("_async.send")
    async_client = Delegated("_async.client")

    def __init__(self, fluid=None):
        self._sync = None
        self._async = None
        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        config = fluid.config

        user = config["MAIL_USERNAME"]
        password = config["MAIL_PASSWORD"]
        if user and not password:
            raise FrameworkException("Missing MAIL_PASSWORD for MAIL_USERNAME.")
        if password and not user:
            raise FrameworkException("Missing MAIL_USERNAME for MAIL_PASSWORD.")

        settings = (
            config["MAIL_SERVER"], config["MAIL_PORT"],
            config["MAIL_USE_TLS"], config["MAIL_USE_STARTTLS"],
            config["MAIL_TIMEOUT"], user, password,
            config["MAIL_DEFAULT_SENDER"]
        )

        self._sync = SyncManager(*settings)
        self._async = AsyncManager(*settings)
