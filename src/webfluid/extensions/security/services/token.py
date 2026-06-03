from fastapi import Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from itsdangerous import URLSafeTimedSerializer
from itsdangerous.exc import BadSignature, SignatureExpired
from webfluid.core.ext import scheduler, db
from webfluid.core.constants import DEBUG
from webfluid.utils.logging import factory as log_factory
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import delete, select
from secrets import token_urlsafe
from datetime import timedelta, datetime, UTC
from typing import Callable
import hmac

from webfluid.extensions.security.models.token import ExpiredToken


class TokenService:
    def __init__(self, secret: str, max_age: int, csrf_cookie: str, csrf_secure: bool):
        self._serializer = URLSafeTimedSerializer(secret)
        self._max_age = max_age
        self._csrf_cookie = csrf_cookie
        self._csrf_secure = csrf_secure
        self.csrf_protect = Depends(self._csrf_protect())

        async def db_cleaner():
            async with db.async_executor(model=ExpiredToken) as e:
                time_diff = datetime.now(UTC) - timedelta(seconds=max_age)
                await e.exec(delete(ExpiredToken).where(
                    ExpiredToken.created_at < time_diff
                ))

        scheduler.add_job(db_cleaner, IntervalTrigger(days=15))

        if not csrf_secure and not DEBUG:
            log_factory.warning("[Security] CSRF cookies are not secure. "
                                "Consider setting SECURITY_CSRF_COOKIE_SECURE=True")

    def generate_token(self, data: dict, salt: str = "csrf") -> str:
        return self._serializer.dumps(data, salt=salt)

    async def validate_token(self, token: str, salt: str = "csrf") -> dict:
        try:
            if salt == "csrf":
                return self._serializer.loads(token, salt=salt, max_age=self._max_age)

            async with db.async_executor(model=ExpiredToken) as e:
                expired = await e.exec(select(ExpiredToken).where(
                    ExpiredToken.token == token
                ))
                if expired.first():
                    raise HTTPException(status_code=403, detail="TOKEN_EXPIRED")

                data = self._serializer.loads(token, salt=salt, max_age=self._max_age)
                await e.insert(ExpiredToken(token))
                return data

        except SignatureExpired:
            raise HTTPException(status_code=403, detail="TOKEN_EXPIRED")

        except BadSignature:
            raise HTTPException(status_code=403, detail="INVALID_TOKEN")

    def csrf_response(self, request: Request) -> JSONResponse:
        raw = token_urlsafe(32)
        csrf_token = self.generate_token({ "csrf": raw })
        request.session["csrf_token"] = raw

        response = JSONResponse(
            content={ "status": "ok" }
        )
        response.set_cookie(
            key="csrf_token",
            value=csrf_token,
            httponly=False,
            secure=self._csrf_secure,
            samesite="lax",
            path="/"
        )
        return response

    def _csrf_protect(self) -> Callable:
        async def wrapped(request: Request):
            if request.method in {"GET", "HEAD", "OPTIONS"}:
                return

            csrf_cookie = request.cookies.get("csrf_token")
            csrf_header = request.headers.get("X-CSRF-Token")
            csrf_session = request.session.get("csrf_token", "")

            if not csrf_cookie or not csrf_header or not csrf_session:
                raise HTTPException(status_code=403, detail="Missing CSRF token")

            cookie_data = await self.validate_token(csrf_cookie)
            header_data = await self.validate_token(csrf_header)
            cookie_val = cookie_data.get("csrf", "")
            header_val = header_data.get("csrf", "")


            if not (cookie_val and header_val):
                raise HTTPException(status_code=403, detail="Invalid CSRF token")

            if not (
                    hmac.compare_digest(cookie_val, csrf_session) and
                    hmac.compare_digest(header_val, csrf_session)
            ):
                raise HTTPException(status_code=403, detail="CSRF mismatch")

        return wrapped
