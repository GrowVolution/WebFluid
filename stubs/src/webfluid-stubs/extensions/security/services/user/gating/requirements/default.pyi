from collections.abc import AsyncGenerator, Callable
from typing import Any

from webfluid.extensions.security.models.user import User
from webfluid.extensions.security.services.token import TokenService

def _resolver_fn(
    token_service: TokenService
) -> Callable[..., AsyncGenerator[User, None]]: ...

class Gate:
    resolve: Callable[..., AsyncGenerator[User, None]]
    depends: Any
    def __init__(self, token_service: TokenService) -> None: ...
