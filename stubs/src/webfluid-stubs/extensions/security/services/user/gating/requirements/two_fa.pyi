from collections.abc import AsyncGenerator, Callable
from typing import Any

from webfluid.extensions.security.models.user import User
from webfluid.extensions.security.services.user.gating.requirements.email_verified import (
    Gate as EmailVerifiedGate,
)

def requirement_fulfilled(user: User) -> bool: ...
def _resolver_fn(
    email_verified_gate: EmailVerifiedGate
) -> Callable[..., AsyncGenerator[User, None]]: ...

class Gate:
    resolve: Callable[..., AsyncGenerator[User, None]]
    depends: Any
    def __init__(self, email_verified_gate: EmailVerifiedGate) -> None: ...
