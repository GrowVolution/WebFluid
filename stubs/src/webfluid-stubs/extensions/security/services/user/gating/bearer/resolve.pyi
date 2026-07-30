from collections.abc import AsyncGenerator

from fastapi import Request

from webfluid.extensions.security.models.user import User

async def resolve_bearer(
    request: Request, grant: str
) -> AsyncGenerator[tuple[User | None, bool], None]: ...
async def bearer_principal(
    request: Request, grant: str
) -> AsyncGenerator[User | None, None]: ...
