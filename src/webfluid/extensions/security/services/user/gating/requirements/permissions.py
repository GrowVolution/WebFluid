from fastapi import Request, HTTPException, Depends
from sqlalchemy import select, func, distinct

from webfluid.extensions.security.models.user import (
    Permission, role_permissions, user_roles
)
from webfluid.extensions.sqlalchemy import SQLAlchemy


async def requirement_fulfilled(user, permissions):
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


def _resolver_fn(two_fa_gate, permissions):
    async def wrapped(request: Request):
        async for user in two_fa_gate.resolve(request):
            if not await requirement_fulfilled(user, permissions):
                raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
            yield user
    return wrapped


class Gate:
    def __init__(self, two_fa_gate):
        self.resolver = lambda permissions: _resolver_fn(two_fa_gate, permissions)
        self.depends = lambda permissions: Depends(self.resolver(permissions))
