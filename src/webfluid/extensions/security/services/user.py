from fastapi import Request, Depends, HTTPException
from webfluid.extensions.sqlalchemy import SQLAlchemy
from sqlalchemy import select
from typing import TYPE_CHECKING, Optional, AsyncGenerator, Callable, Any

from webfluid.extensions.security.models.user import User

if TYPE_CHECKING:
    from fastapi.params import Depends as DependsParam
    from webfluid.extensions.security.services import TokenService


class UserService:
    def __init__(self, token_service: "TokenService"):
        self.current_user = Depends(UserService._current_user)
        self.require_user = Depends(self._require_user(token_service))
        self.require_admin = Depends(self._require_admin())

    @staticmethod
    async def _current_user(request: Request) -> AsyncGenerator[Optional[User]]:
        if "user_id" not in request.session:
            yield None
            return

        db = SQLAlchemy.get_instance()
        async with db.async_executor(model=User) as e:
            results = await e.exec(
                select(User).where(
                    User.id == request.session["user_id"]
                )
            )
            yield results.first()

    def _require_user(self, token_service: "TokenService") -> Callable:
        async def wrapped(
                user: User = self.current_user,
                _ = token_service.csrf_protect
        ) -> AsyncGenerator[User]:
            if not user:
                raise HTTPException(status_code=401, detail="NOT_AUTHENTICATED")
            yield user
        return wrapped

    @staticmethod
    def is_admin(user: User) -> bool:
        for role in user.roles:
            if role.is_admin: return True
        return False

    def _require_admin(self) -> Callable:
        async def wrapped(
                user: User = self.require_user
        ) -> AsyncGenerator[Optional[User]]:
            if not UserService.is_admin(user):
                raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
            yield user
        return wrapped

    @staticmethod
    def has_roles(user: User, roles: list[str]) -> bool:
        required_roles = set(roles)
        for role in user.roles:
            if role.name in roles:
                required_roles.remove(role.name)
        return len(required_roles) == 0

    def require_roles(self, roles: list[str]) -> Any["DependsParam"]:
        async def wrapped(
                user: User = self.require_user
        ) -> AsyncGenerator[User]:
            if not UserService.has_roles(user, roles):
                raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
            yield user
        return Depends(wrapped)

    @staticmethod
    def has_any_role(user: User, roles: list[str]) -> bool:
        for role in user.roles:
            if role.name in roles:
                return True
        return False

    def require_any_role(self, roles: list[str]) -> Any["DependsParam"]:
        async def wrapped(
                user: User = self.require_user
        ) -> AsyncGenerator[User]:
            if not UserService.has_any_role(user, roles):
                raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
            yield user
        return Depends(wrapped)

    @staticmethod
    def has_permissions(user: User, permissions: list[str]) -> bool:
        required_permissions = set(permissions)
        for role in user.roles:
            for perm in role.permissions:
                if perm.name in permissions:
                    required_permissions.remove(perm.name)

            if len(required_permissions) == 0:
                return True
        return False

    def require_permissions(self, permissions: list[str]) -> Any["DependsParam"]:
        async def wrapped(
                user: User = self.require_user
        ) -> AsyncGenerator[User]:
            if not UserService.has_permissions(user, permissions):
                raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
            yield user
        return Depends(wrapped)

    @staticmethod
    def has_any_permission(user: User, permissions: list[str]) -> bool:
        for role in user.roles:
            for perm in role.permissions:
                if perm.name in permissions:
                    return True
        return False

    def require_any_permission(self, permissions: list[str]) -> Any["DependsParam"]:
        async def wrapped(
                user: User = self.require_user
        ) -> AsyncGenerator[User]:
            if not UserService.has_any_permission(user, permissions):
                raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
            yield user
        return Depends(wrapped)

    @classmethod
    def check_requirement(cls, user: User, r: dict) -> bool:
        requirement = r.get("requirement")
        if not requirement or not isinstance(requirement, str):
            raise ValueError("Invalid requirement format.")

        if requirement == "is_authenticated":
            return user is not None

        if requirement not in {
            "is_admin", "has_roles", "has_any_role",
            "has_permissions", "has_any_permission"
        }:
            raise ValueError("Invalid requirement format: Invalid requirement.")

        if requirement != "is_admin" and cls.is_admin(user): return True

        param = None

        if requirement in {
            "has_roles", "has_any_role"
        } and ("roles" not in r or not isinstance(r["roles"], list)):
            raise ValueError("Invalid requirement format: Invalid or missing 'roles' field.")

        elif requirement in {
            "has_roles", "has_any_role"
        }:
            param = r["roles"]

        if requirement in {
            "has_permissions", "has_any_permission"
        } and ("permissions" not in r or not isinstance(r["permissions"], list)):
            raise ValueError("Invalid requirement format: Invalid or missing 'permissions' field.")

        elif requirement in {
            "has_permissions", "has_any_permission"
        }:
            param = r["permissions"]

        check = getattr(cls, requirement)
        return check(user, param) if param else check(user)
