from .resolve import resolve_bearer, bearer_principal
from .any import Gate as RequirementOrGrantGate
from .all import Gate as RequirementAndGrantGate

__all__ = [
    "resolve_bearer", "bearer_principal",
    "RequirementOrGrantGate",
    "RequirementAndGrantGate"
]
