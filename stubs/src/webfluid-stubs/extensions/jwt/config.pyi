from typing import Any

class JWTConfig:
    rotary_interval: int
    secret_length: int
    expiry_days: int
    algorithm: str
    issuer: str
    audiences: dict[str, str]
    def __init__(self, config: dict[str, Any]) -> None: ...
    def audience(self, name: str) -> str: ...
