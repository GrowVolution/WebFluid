from collections.abc import AsyncGenerator, Callable
from typing import Any

from webfluid.extensions.security.models.user import User
from webfluid.extensions.security.services.user.gating.requirements.two_fa import (
    Gate as TwoFaGate,
)

def resolver_fn(
    two_fa_gate: TwoFaGate, requirement: dict[str, Any],
    grant: str, _skip_check: bool = False
) -> Callable[..., AsyncGenerator[User, None]]: ...

class Gate:
    resolver: Callable[
        [dict[str, Any], str], Callable[..., AsyncGenerator[User, None]]
    ]
    depends: Callable[[dict[str, Any], str], Any]
    def __init__(self, two_fa_gate: TwoFaGate) -> None: ...
