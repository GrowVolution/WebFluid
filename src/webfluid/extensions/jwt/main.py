from .rotate import add_job as add_key_rotation_job
from .encode import Encoder
from .decode import Decoder

from webfluid.extensions.base import FluidExtension
from webfluid.core.constants import EXT_SCHEDULING, EXT_CACHE
from webfluid.exceptions import FrameworkException


class JWTManager(FluidExtension):
    def __init__(self, fluid=None):
        self._secret_rotary_interval = 15
        self._secret_length = 128
        self._token_expiry_days = 30
        self._token_algorithm = "HS256"
        self._token_issuer = "WebFluid"
        self._token_audiences = {
            "default": "Application"
        }

        self._encoder = None
        self._decoder = None

        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        if not EXT_SCHEDULING:
            raise FrameworkException("EXT_SCHEDULING is required for JWTManager to work.")
        if not EXT_CACHE:
            raise FrameworkException("EXT_CACHE is required for JWTManager to work.")

        self._secret_rotary_interval = fluid.config.get(
            "JWT_ROTARY_INTERVAL", self._secret_rotary_interval
        )
        self._secret_length = fluid.config.get(
            "JWT_SECRET_LENGTH", self._secret_length
        )

        self._token_expiry_days = fluid.config.get("JWT_EXPIRY_DAYS", self._token_expiry_days)
        self._token_algorithm = fluid.config.get("JWT_ALGORITHM", self._token_algorithm)
        self._token_issuer = fluid.config.get("JWT_ISSUER", self._token_issuer)
        self._token_audiences = fluid.config.get("JWT_AUDIENCES", self._token_audiences)

        self._encoder = Encoder(self)
        self._decoder = Decoder(self)

        add_key_rotation_job(fluid, self)

    def _ensure_initialized(self):
        if not self._encoder or not self._decoder:
            raise FrameworkException("JWTManager.expand_fluid() has not been called.")

    @property
    def encode(self):
        self._ensure_initialized()
        return self._encoder.encode

    @property
    def aencode(self):
        self._ensure_initialized()
        return self._encoder.aencode

    @property
    def decode(self):
        self._ensure_initialized()
        return self._decoder.decode

    @property
    def adecode(self):
        self._ensure_initialized()
        return self._decoder.adecode
