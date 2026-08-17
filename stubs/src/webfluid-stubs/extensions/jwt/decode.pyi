from re import Pattern
from typing import Any

from webfluid.extensions.jwt.config import JWTConfig

_KID: Pattern[str]

def _kid(token: str) -> str | None: ...

class Decoder:
    _config: JWTConfig
    def __init__(self, config: JWTConfig) -> None: ...
    def _payload(
        self, token: str, audience: str, secret: str | None
    ) -> dict[str, Any]: ...
    def decode(self, token: str, audience: str = "default") -> dict[str, Any]: ...
    async def adecode(self, token: str, audience: str = "default") -> dict[str, Any]: ...
