from fastapi import Request, HTTPException, Depends

from ...current import current_user


def _resolver_fn(token_service):
    async def wrapped(request: Request):
        await token_service.csrf_protect_fn(request)
        async for user in current_user(request):
            if not user:
                raise HTTPException(status_code=401, detail="NOT_AUTHENTICATED")
            yield user
    return wrapped


class Gate:
    def __init__(self, token_service):
        self.resolve = _resolver_fn(token_service)
        self.depends = Depends(self.resolve)
