from typing import Any

from webfluid.extensions.jwt.main import JWTManager

class Encoder:
    _jwt_manager: JWTManager
    def __init__(self, jwt_manager: JWTManager) -> None: ...
    def _encode(
        self, payload: dict[str, Any], audience: str, secret: str,
        expire: int | None, kid: str
    ) -> str: ...
    def encode(
        self, payload: dict[str, Any], audience: str = "default",
        expire: int | None = None
    ) -> str: ...
    async def aencode(
        self, payload: dict[str, Any], audience: str = "default",
        expire: int | None = None
    ) -> str: ...
