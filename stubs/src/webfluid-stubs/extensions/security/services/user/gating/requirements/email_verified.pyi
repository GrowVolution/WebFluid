from collections.abc import AsyncGenerator, Callable
from typing import Any

from webfluid.extensions.security.models.user import User
from webfluid.extensions.security.services.user.gating.requirements.default import (
    Gate as DefaultGate,
)

def requirement_fulfilled(user: User) -> bool: ...
def _resolver_fn(
    default_gate: DefaultGate
) -> Callable[..., AsyncGenerator[User, None]]: ...

class Gate:
    resolve: Callable[..., AsyncGenerator[User, None]]
    depends: Any
    def __init__(self, default_gate: DefaultGate) -> None: ...
