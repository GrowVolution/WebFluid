from fastapi import Request, HTTPException, Depends


def requirement_fulfilled(user):
    if user.totp_secret is not None and user.totp_secret.confirmed:
        return True
    return len(user.webauthn_credentials) > 0


def _resolver_fn(default_gate):
    async def wrapped(request: Request):
        async for user in default_gate.resolve(request):
            if requirement_fulfilled(user) \
                    and not request.session.get("2fa_verified"):
                raise HTTPException(status_code=401, detail="TWO_FA_REQUIRED")
            yield user
    return wrapped


class Gate:
    def __init__(self, email_verified_gate):
        self.resolve = _resolver_fn(email_verified_gate)
        self.depends = Depends(self.resolve)
