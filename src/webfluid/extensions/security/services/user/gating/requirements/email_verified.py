from fastapi import Request, HTTPException, Depends


def requirement_fulfilled(user):
    return user.email and user.email_verified


def _resolver_fn(default_gate):
    async def wrapped(request: Request):
        async for user in default_gate.resolve(request):
            if not requirement_fulfilled(user):
                raise HTTPException(status_code=401, detail="EMAIL_NOT_VERIFIED")
            yield user
    return wrapped


class Gate:
    def __init__(self, default_gate):
        self.resolve = _resolver_fn(default_gate)
        self.depends = Depends(self.resolve)