from fastapi import Depends

from .current import current_user
from .gating import requirements, bearer, check_requirement


class UserService:
    current_user_fn = staticmethod(current_user)
    current_user = Depends(current_user)

    resolve_bearer = staticmethod(bearer.resolve_bearer)
    bearer_principal = staticmethod(bearer.bearer_principal)

    has_2fa = staticmethod(requirements.has_2fa)
    is_admin = staticmethod(requirements.is_admin)
    has_roles = staticmethod(requirements.has_roles)
    has_any_role = staticmethod(requirements.has_any_role)
    has_permissions = staticmethod(requirements.has_permissions)
    has_any_permission = staticmethod(requirements.has_any_permission)
    check_requirement = staticmethod(check_requirement)

    def __init__(self, token_service):
        self._default_gate = requirements.DefaultGate(token_service)
        self._2fa_gate = requirements.TwoFaGate(self._default_gate)
        self._admin_gate = requirements.AdminGate(self._2fa_gate)
        self._roles_gate = requirements.RolesGate(self._2fa_gate)
        self._any_role_gate = requirements.AnyRoleGate(self._2fa_gate)
        self._permissions_gate = requirements.PermissionsGate(self._2fa_gate)
        self._any_permission_gate = requirements.AnyPermissionGate(self._2fa_gate)
        self._requirement_or_grant_gate = bearer.RequirementOrGrantGate(self._2fa_gate)
        self._requirement_and_grant_gate = bearer.RequirementAndGrantGate(self._2fa_gate)

    @property
    def require_user_fn(self):
        return self._default_gate.resolve

    @property
    def require_user(self):
        return self._default_gate.depends

    @property
    def require_2fa_fn(self):
        return self._2fa_gate.resolve

    @property
    def require_2fa(self):
        return self._2fa_gate.depends

    @property
    def require_admin_fn(self):
        return self._admin_gate.resolve

    @property
    def require_admin(self):
        return self._admin_gate.depends

    def require_roles_fn(self, roles):
        return self._roles_gate.resolver(roles)

    def require_roles(self, roles):
        return self._roles_gate.depends(roles)

    def require_any_role_fn(self, roles):
        return self._any_role_gate.resolver(roles)

    def require_any_role(self, roles):
        return self._any_role_gate.depends(roles)

    def require_permissions_fn(self, permissions):
        return self._permissions_gate.resolver(permissions)

    def require_permissions(self, permissions):
        return self._permissions_gate.depends(permissions)

    def require_any_permission_fn(self, permissions):
        return self._any_permission_gate.resolver(permissions)

    def require_any_permission(self, permissions):
        return self._any_permission_gate.depends(permissions)

    def requirement_or_grant_fn(self, requirement, grant):
        return self._requirement_or_grant_gate.resolver(requirement, grant)

    def requirement_or_grant(self, requirement, grant):
        return self._requirement_or_grant_gate.depends(requirement, grant)

    def requirement_and_grant_fn(self, requirement, grant):
        return self._requirement_and_grant_gate.resolver(requirement, grant)

    def requirement_and_grant(self, requirement, grant):
        return self._requirement_and_grant_gate.depends(requirement, grant)
