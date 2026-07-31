from collections.abc import Awaitable, Callable
from typing import Any

from webfluid import Fluid
from webfluid.extensions.base import FluidExtension
from webfluid.extensions.jwt.config import JWTConfig
from webfluid.extensions.jwt.decode import Decoder
from webfluid.extensions.jwt.encode import Encoder

class JWTManager(FluidExtension):
    _config: JWTConfig | None
    _encoder: Encoder | None
    _decoder: Decoder | None
    encode: Callable[..., str]
    aencode: Callable[..., Awaitable[str]]
    decode: Callable[..., dict[str, Any]]
    adecode: Callable[..., Awaitable[dict[str, Any]]]
    def __init__(self, fluid: Fluid | None = None) -> None: ...
    def expand_fluid(self, fluid: Fluid, *args: Any, **kwargs: Any) -> None: ...
