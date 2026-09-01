from typing import Any

from webfluid import Fluid
from webfluid.extensions.base import FluidExtension
from webfluid.extensions.security.services import (
    HashService, OAuthService, TokenService, UserService
)

_models: tuple[str, ...]

def _resolve_secret(fluid: Fluid) -> str: ...
def _bind_models(bind: str) -> None: ...

class Security(FluidExtension):
    _user_service: UserService | None
    _token_service: TokenService | None
    _hash_service: HashService | None
    _oauth_service: OAuthService | None
    user_service: UserService
    token_service: TokenService
    hash_service: HashService
    oauth_service: OAuthService
    def __init__(self, fluid: Fluid | None = None) -> None: ...
    def expand_fluid(self, fluid: Fluid, *args: Any, **kwargs: Any) -> None: ...
