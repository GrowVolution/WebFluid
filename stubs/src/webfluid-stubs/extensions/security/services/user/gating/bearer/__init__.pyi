from webfluid.extensions.security.services.user.gating.bearer.resolve import (
    resolve_bearer as resolve_bearer,
    bearer_principal as bearer_principal,
)
from webfluid.extensions.security.services.user.gating.bearer.any import (
    Gate as RequirementOrGrantGate,
)
from webfluid.extensions.security.services.user.gating.bearer.all import (
    Gate as RequirementAndGrantGate,
)

__all__ = [
    "resolve_bearer", "bearer_principal",
    "RequirementOrGrantGate",
    "RequirementAndGrantGate",
]
