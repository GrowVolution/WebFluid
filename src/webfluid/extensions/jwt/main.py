from .config import JWTConfig
from .rotate import add_job as add_key_rotation_job
from .encode import Encoder
from .decode import Decoder

from webfluid.extensions.base import Delegated, FluidExtension
from webfluid.core.constants import EXT_SCHEDULING, EXT_CACHE
from webfluid.exceptions import FrameworkException


class JWTManager(FluidExtension):
    encode = Delegated("_encoder.encode")
    aencode = Delegated("_encoder.aencode")
    decode = Delegated("_decoder.decode")
    adecode = Delegated("_decoder.adecode")

    def __init__(self, fluid=None):
        self._config = None
        self._encoder = None
        self._decoder = None

        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        if not EXT_SCHEDULING:
            raise FrameworkException("EXT_SCHEDULING is required for JWTManager to work.")
        if not EXT_CACHE:
            raise FrameworkException("EXT_CACHE is required for JWTManager to work.")

        self._config = JWTConfig(fluid.config)
        self._encoder = Encoder(self._config)
        self._decoder = Decoder(self._config)

        add_key_rotation_job(fluid, self._config)
