from fastapi import Request, HTTPException, Depends
from sqlalchemy import select, func, distinct

from webfluid.extensions.security.models.user import Role, user_roles
from webfluid.extensions.sqlalchemy import SQLAlchemy


async def requirement_fulfilled(user, roles):
    required = set(roles)
    if not required: return True

    db = SQLAlchemy.get_instance()
    async with db.ensured_async_executor(model=Role) as e:
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
