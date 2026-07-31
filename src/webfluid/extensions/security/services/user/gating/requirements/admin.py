from fastapi import Request, HTTPException, Depends
from sqlalchemy import select

from webfluid.extensions.security.models.user import Role, user_roles
from webfluid.extensions.sqlalchemy import SQLAlchemy


async def requirement_fulfilled(user):
    db = SQLAlchemy.get_instance()
    async with db.ensured_async_executor(model=Role) as e:
        result = await e.exec(
            select(
                select(Role.id)
                .join(user_roles, user_roles.c.role_id == Role.id)
                .where(
                    user_roles.c.user_id == user.id,
                    Role.is_admin == True
                ).exists()
            ),
            scalars=False
        )
        return bool(result.scalar())


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
