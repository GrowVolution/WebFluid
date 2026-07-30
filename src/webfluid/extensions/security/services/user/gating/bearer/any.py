from fastapi import Request, HTTPException, Depends

from .resolve import resolve_bearer
from ..check import check_requirement


def resolver_fn(two_fa_gate, requirement, grant, _skip_check=False):
    async def wrapped(request: Request):
        try:
            async for user in two_fa_gate.resolve(request):
                if not _skip_check and not await check_requirement(user, requirement):
                    raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
                yield user

        except ValueError as e:
            from webfluid.utils.logging import factory as log_factory
            log_factory.exception(e)
            raise HTTPException(status_code=500)

        except HTTPException as session_exc:
            async for principal, token_present in resolve_bearer(
                    request, grant
            ):
                if principal is None and token_present:
                    raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
                elif principal is None: raise session_exc
                yield principal
    return wrapped


class Gate:
    def __init__(self, two_fa_gate):
        self.resolver = lambda requirement, grant: resolver_fn(
            two_fa_gate, requirement, grant
        )
        self.depends = lambda requirement, grant: Depends(
            self.resolver(requirement, grant)
        )
