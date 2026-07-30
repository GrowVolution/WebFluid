from collections.abc import AsyncGenerator

from fastapi import Request

from webfluid.extensions.security.models.user import User

async def current_user(request: Request) -> AsyncGenerator[User | None, None]: ...
