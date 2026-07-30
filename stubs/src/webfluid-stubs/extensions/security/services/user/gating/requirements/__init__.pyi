from webfluid.extensions.security.services.user.gating.requirements.default import (
    Gate as DefaultGate,
)
from webfluid.extensions.security.services.user.gating.requirements.two_fa import (
    Gate as TwoFaGate, requirement_fulfilled as has_2fa,
)
from webfluid.extensions.security.services.user.gating.requirements.admin import (
    Gate as AdminGate, requirement_fulfilled as is_admin,
)
from webfluid.extensions.security.services.user.gating.requirements.roles import (
    Gate as RolesGate, requirement_fulfilled as has_roles,
)
from webfluid.extensions.security.services.user.gating.requirements.any_role import (
    Gate as AnyRoleGate, requirement_fulfilled as has_any_role,
)
from webfluid.extensions.security.services.user.gating.requirements.permissions import (
    Gate as PermissionsGate, requirement_fulfilled as has_permissions,
)
from webfluid.extensions.security.services.user.gating.requirements.any_permission import (
    Gate as AnyPermissionGate, requirement_fulfilled as has_any_permission,
)

__all__ = [
    "DefaultGate",
    "TwoFaGate", "has_2fa",
    "AdminGate", "is_admin",
    "RolesGate", "has_roles",
    "AnyRoleGate", "has_any_role",
    "PermissionsGate", "has_permissions",
    "AnyPermissionGate", "has_any_permission",
]
