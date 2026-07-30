from collections.abc import AsyncGenerator, Callable
from typing import Any

from webfluid.extensions.security.models.user import User
from webfluid.extensions.security.services.user.gating.requirements.two_fa import (
    Gate as TwoFaGate,
)

async def requirement_fulfilled(user: User, roles: list[str]) -> bool: ...
def _resolver_fn(
    two_fa_gate: TwoFaGate, roles: list[str]
) -> Callable[..., AsyncGenerator[User, None]]: ...

class Gate:
    resolver: Callable[[list[str]], Callable[..., AsyncGenerator[User, None]]]
    depends: Callable[[list[str]], Any]
    def __init__(self, two_fa_gate: TwoFaGate) -> None: ...
