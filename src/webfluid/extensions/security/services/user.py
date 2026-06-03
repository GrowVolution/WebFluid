from fastapi import Request, Depends, HTTPException
from webfluid.core.ext import db
from sqlalchemy import select
from typing import TYPE_CHECKING, Optional, AsyncGenerator, Callable, Any

from webfluid.extensions.security.models.user import User

if TYPE_CHECKING:
    from fastapi.params import Depends as DependsParam
    from webfluid.extensions.security.services.token import TokenService


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

        async with db.async_executor(model=User) as e:
            results = await e.exec(
                select(User).where(
                    User.id == request.session["user_id"]
                )
            )
            yield results.first()

    def _require_user(self, token_service: "TokenService") -> Callable:
        async def wrapped(
                request: Request,
                user: User = self.current_user,
                _ = token_service.csrf_protect
        ) -> AsyncGenerator[User]:
            if not user:
                raise HTTPException(status_code=401, detail="NOT_AUTHENTICATED")

            if "pending_email" in request.session \
                    and user.email == request.session["pending_email"]:
                request.session.pop("pending_email")

            yield user
        return wrapped

    def _require_admin(self) -> Callable:
        async def wrapped(
                user: User = self.require_user
        ) -> AsyncGenerator[Optional[User]]:
            for role in user.roles:
                if role.is_admin:
                    yield user
                    return
            raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
        return wrapped

    def require_roles(self, roles: list[str]) -> Any["DependsParam"]:
        async def wrapped(
                user: User = self.require_user
        ) -> AsyncGenerator[User]:
            required_roles = set(roles)
            for role in user.roles:
                if role.name in roles:
                    required_roles.remove(role.name)

            if len(required_roles) > 0:
                raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")

            yield user
        return Depends(wrapped)

    def require_any_role(self, roles: list[str]) -> Any["DependsParam"]:
        async def wrapped(
                user: User = self.require_user
        ) -> AsyncGenerator[User]:
            for role in user.roles:
                if role.name in roles:
                    yield user
                    return

            raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
        return Depends(wrapped)

    def require_permissions(self, permissions: list[str]) -> Any["DependsParam"]:
        async def wrapped(
                user: User = self.require_user
        ) -> AsyncGenerator[User]:
            required_permissions = set(permissions)
            for role in user.roles:
                for perm in role.permissions:
                    if perm.name in permissions:
                        required_permissions.remove(perm.name)

                if len(required_permissions) == 0:
                    yield user
                    return

            raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
        return Depends(wrapped)

    def require_any_permission(self, permissions: list[str]) -> Any["DependsParam"]:
        async def wrapped(
                user: User = self.require_user
        ) -> AsyncGenerator[User]:
            for role in user.roles:
                for perm in role.permissions:
                    if perm.name in permissions:
                        yield user
                        return

            raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
        return Depends(wrapped)
