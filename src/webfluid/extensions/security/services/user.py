from fastapi import Request, Depends, HTTPException
from sqlalchemy import select, func, distinct
import asyncio

from webfluid.core.constants import EXT_JWT
from webfluid.extensions.sqlalchemy import SQLAlchemy
from webfluid.extensions.security.models.user import (
    User, Role, Permission, user_roles, role_permissions
)


class UserService:
    def __init__(self, token_service):
        self._token_service = token_service
        self.current_user = Depends(UserService.current_user_fn)

        self.require_user_fn = UserService._require_user(token_service)
        self.require_user = Depends(self.require_user_fn)

        self.require_2fa_fn = self._require_2fa()
        self.require_2fa = Depends(self.require_2fa_fn)

        self.require_admin_fn = self._require_admin()
        self.require_admin = Depends(self.require_admin_fn)

    @staticmethod
    async def current_user_fn(request: Request):
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

    @staticmethod
    async def resolve_bearer(request: Request, grant: str):
        if not EXT_JWT: yield None, False; return
        scheme, _, raw = request.headers.get("Authorization", "").partition(" ")
        raw = raw.strip()
        if scheme.lower() != "bearer" or not raw: yield None, False; return

        from webfluid.core.ext import jwt
        try: payload = await jwt.adecode(raw)
        except Exception as exc:
            from webfluid.utils.logging import factory as log_factory
            log_factory.debug(f"[Security] Rejected bearer token: {exc}")
            yield None, False; return

        sub = payload.get("sub")
        if sub is None: yield None, False; return

        grants = payload.get("permissions")
        if not isinstance(grants, list) or grant not in grants:
            yield None, True; return

        db = SQLAlchemy.get_instance()
        async with db.async_executor(model=User) as e:
            result = await e.exec(select(User).where(User.id == int(sub)))
            yield result.first(), True

    @staticmethod
    async def bearer_principal(request: Request, grant: str):
        async for user, _ in UserService.resolve_bearer(request, grant): yield user

    @staticmethod
    def _require_user(token_service):
        async def wrapped(request: Request):
            await token_service.csrf_protect_fn(request)
            async for user in UserService.current_user_fn(request):
                if not user:
                    raise HTTPException(status_code=401, detail="NOT_AUTHENTICATED")
                yield user
        return wrapped

    @staticmethod
    def has_2fa(user: User) -> bool:
        if user.totp_secret is not None and user.totp_secret.confirmed:
            return True
        return len(user.webauthn_credentials) > 0

    def _require_2fa(self):
        async def wrapped(request: Request):
            async for user in self.require_user_fn(request):
                if UserService.has_2fa(user) and not request.session.get("2fa_verified"):
                    raise HTTPException(status_code=401, detail="TWO_FA_REQUIRED")
                yield user
        return wrapped

    @staticmethod
    async def is_admin(user: User) -> bool:
        e = SQLAlchemy.get_instance().current_async_executor
        result = await e.exec(
            select(Role)
            .join(user_roles, user_roles.c.role_id == Role.id)
            .where(
                user_roles.c.user_id == user.id,
                Role.is_admin == True
            ).limit(1)
        )
        return result.first() is not None

    def _require_admin(self):
        async def wrapped(request: Request):
            async for user in self.require_2fa_fn(request):
                if not await UserService.is_admin(user):
                    raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
                yield user
        return wrapped

    @staticmethod
    async def has_roles(user: User, roles: list[str]) -> bool:
        required = set(roles)
        if not required: return True

        e = SQLAlchemy.get_instance().current_async_executor
        result = await e.exec(
            select(func.count(distinct(Role.name)))
            .select_from(Role)
            .join(user_roles, user_roles.c.role_id == Role.id)
            .where(
                user_roles.c.user_id == user.id,
                Role.name.in_(required)
            ),
            scalars=False
        )
        return result.scalar() == len(required)

    def require_roles_fn(self, roles: list[str]):
        async def wrapped(request: Request):
            async for user in self.require_2fa_fn(request):
                if not await UserService.has_roles(user, roles):
                    raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
                yield user
        return wrapped

    def require_roles(self, roles: list[str]):
        return Depends(self.require_roles_fn(roles))

    @staticmethod
    async def has_any_role(user: User, roles: list[str]) -> bool:
        if not roles: return False

        e = SQLAlchemy.get_instance().current_async_executor
        result = await e.exec(
            select(Role.id)
            .join(user_roles, user_roles.c.role_id == Role.id)
            .where(
                user_roles.c.user_id == user.id,
                Role.name.in_(roles)
            )
            .limit(1)
        )
        return result.first() is not None

    def require_any_role_fn(self, roles: list[str]):
        async def wrapped(request: Request):
            async for user in self.require_2fa_fn(request):
                if not await UserService.has_any_role(user, roles):
                    raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
                yield user
        return wrapped

    def require_any_role(self, roles: list[str]):
        return Depends(self.require_any_role_fn(roles))

    @staticmethod
    async def has_permissions(user: User, permissions: list[str]) -> bool:
        required = set(permissions)
        if not required: return True

        e = SQLAlchemy.get_instance().current_async_executor
        result = await e.exec(
            select(func.count(distinct(Permission.name)))
            .select_from(Permission)
            .join(
                role_permissions,
                role_permissions.c.permission_id == Permission.id
            )
            .join(
                user_roles,
                user_roles.c.role_id == role_permissions.c.role_id
            )
            .where(
                user_roles.c.user_id == user.id,
                Permission.name.in_(required)
            ),
            scalars=False
        )
        return result.scalar() == len(required)

    def require_permissions_fn(self, permissions: list[str]):
        async def wrapped(request: Request):
            async for user in self.require_2fa_fn(request):
                if not await UserService.has_permissions(user, permissions):
                    raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
                yield user
        return wrapped

    def require_permissions(self, permissions: list[str]):
        return Depends(self.require_permissions_fn(permissions))

    @staticmethod
    async def has_any_permission(user: User, permissions: list[str]) -> bool:
        if not permissions: return False

        e = SQLAlchemy.get_instance().current_async_executor
        result = await e.exec(
            select(Permission.id)
            .join(
                role_permissions,
                role_permissions.c.permission_id == Permission.id
            )
            .join(
                user_roles,
                user_roles.c.role_id == role_permissions.c.role_id
            )
            .where(
                user_roles.c.user_id == user.id,
                Permission.name.in_(permissions)
            )
            .limit(1)
        )
        return result.first() is not None

    def require_any_permission_fn(self, permissions: list[str]):
        async def wrapped(request: Request):
            async for user in self.require_2fa_fn(request):
                if not await UserService.has_any_permission(user, permissions):
                    raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
                yield user
        return wrapped

    def require_any_permission(self, permissions: list[str]):
        return Depends(self.require_any_permission_fn(permissions))

    def requirement_or_grant_fn(self, requirement: dict, grant: str):
        async def wrapped(request: Request):
            try:
                async for user in self.require_2fa_fn(request):
                    if not await UserService.check_requirement(user, requirement):
                        raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
                    yield user

            except ValueError as e:
                from webfluid.utils.logging import factory as log_factory
                log_factory.exception(e)
                raise HTTPException(status_code=500)

            except HTTPException as session_exc:
                async for principal, token_present in UserService.resolve_bearer(
                    request, grant
                ):
                    if principal is None and token_present:
                        raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
                    elif principal is None: raise session_exc
                    yield principal
        return wrapped

    def requirement_or_grant(self, requirement: dict, grant: str):
        return Depends(self.requirement_or_grant_fn(requirement, grant))

    def requirement_and_grant_fn(self, requirement: dict, grant: str):
        async def wrapped(request: Request):
            resolve = self.requirement_or_grant_fn(requirement, grant)
            async for user in resolve(request):
                if not await UserService.check_requirement(user, requirement):
                    raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
                yield user
        return wrapped

    def requirement_and_grant(self, requirement: dict, grant: str):
        return Depends(self.requirement_and_grant_fn(requirement, grant))

    @classmethod
    async def check_requirement(cls, user: User, r: dict) -> bool:
        requirement = r.get("requirement")
        if not requirement or not isinstance(requirement, str):
            raise ValueError("Invalid requirement format.")

        if requirement == "is_authenticated":
            return user is not None

        if requirement not in {
            "is_admin", "has_2fa", "has_roles", "has_any_role",
            "has_permissions", "has_any_permission"
        }:
            raise ValueError("Invalid requirement format: Invalid requirement.")

        if await cls.is_admin(user): return True

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
        result = check(user, param) if param else check(user)
        if asyncio.iscoroutine(result): result = await result
        return result
