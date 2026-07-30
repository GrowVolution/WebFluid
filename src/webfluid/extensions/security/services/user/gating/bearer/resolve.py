from sqlalchemy import select

from webfluid.core.constants import EXT_JWT
from webfluid.extensions.sqlalchemy import SQLAlchemy
from webfluid.extensions.security.models.user import User


async def resolve_bearer(request, grant):
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


async def bearer_principal(request, grant):
    async for user, _ in resolve_bearer(request, grant): yield user
