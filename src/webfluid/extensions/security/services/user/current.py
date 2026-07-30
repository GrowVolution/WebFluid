from fastapi import Request
from sqlalchemy import select

from webfluid.extensions.security.models import User
from webfluid.extensions.sqlalchemy import SQLAlchemy


async def current_user(request: Request):
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
