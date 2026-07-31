from typing import Any

from webfluid.extensions.jwt.config import JWTConfig

class Encoder:
    _config: JWTConfig
    def __init__(self, config: JWTConfig) -> None: ...
    def _encode(
        self, payload: dict[str, Any], audience: str,
        secret: str, expire: int | None, kid: str
    ) -> str: ...
    def encode(
        self, payload: dict[str, Any],
        audience: str = "default", expire: int | None = None
    ) -> str: ...
    async def aencode(
        self, payload: dict[str, Any],
        audience: str = "default", expire: int | None = None
    ) -> str: ...
