from fastapi import Request, HTTPException, Depends

from ..check import check_requirement


def _resolver_fn(two_fa_gate, requirement, grant):
    from .any import resolver_fn
    async def wrapped(request: Request):
        resolve = resolver_fn(two_fa_gate, requirement, grant, True)
        async for user in resolve(request):
            if not await check_requirement(user, requirement):
                raise HTTPException(status_code=403, detail="NOT_AUTHORIZED")
            yield user
    return wrapped


class Gate:
    def __init__(self, two_fa_gate):
        self.resolver = lambda requirement, grant: _resolver_fn(
            two_fa_gate, requirement, grant
        )
        self.depends = lambda requirement, grant: Depends(
            self.resolver(requirement, grant)
        )
