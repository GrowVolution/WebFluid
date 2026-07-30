from fastapi import Request, HTTPException, Depends
from sqlalchemy import select

from webfluid.extensions.security.models.user import Role, user_roles
from webfluid.extensions.sqlalchemy import SQLAlchemy


async def requirement_fulfilled(user, roles):
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


def _resolver_fn(two_fa_gate, roles):
    async def wrapped(request: Request):
        async for user in two_fa_gate.resolve(request):
            if not await requirement_fulfilled(user, roles):
                raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
            yield user
    return wrapped


class Gate:
    def __init__(self, two_fa_gate):
        self.resolver = lambda roles: _resolver_fn(two_fa_gate, roles)
        self.depends = lambda roles: Depends(self.resolver(roles))
