from fastapi import Request, HTTPException, Depends
from sqlalchemy import select

from webfluid.extensions.security.models.user import Role, user_roles
from webfluid.extensions.sqlalchemy import SQLAlchemy


async def requirement_fulfilled(user):
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


def _resolver_fn(two_fa_gate):
    async def wrapped(request: Request):
        async for user in two_fa_gate.resolve(request):
            if not await requirement_fulfilled(user):
                raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
            yield user
    return wrapped


class Gate:
    def __init__(self, two_fa_gate):
        self.resolve = _resolver_fn(two_fa_gate)
        self.depends = Depends(self.resolve)
