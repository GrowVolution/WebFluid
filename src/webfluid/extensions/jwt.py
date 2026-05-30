from uuid import uuid4
from datetime import datetime, timedelta, UTC
from apscheduler.triggers.interval import IntervalTrigger
from typing import TYPE_CHECKING, Optional
import jwt, secrets

from webfluid.extensions.base import FluidExtension
from webfluid.core.constants import EXT_SCHEDULING, EXT_CACHE
from webfluid.exceptions import FrameworkException

if TYPE_CHECKING:
    from webfluid.core.fluid import Fluid


class JWTManager(FluidExtension):
    def __init__(self, fluid: Optional["Fluid"] = None):
        self._current_key = None
        self._secret_rotary_interval = 15
        self._secret_length = 128
        self._token_expiry_days = 30
        self._token_algorithm = "HS256"
        self._token_issuer = "WebFluid"
        self._token_audiences = {
            "default": "Application"
        }

        super().__init__(fluid)

    async def _rotate_secret(self):
        from webfluid.core.ext import cache
        self._current_key = uuid4().hex
        await cache.aset(
            f"jwt:{self._current_key}",
            secrets.token_hex(self._secret_length),
            self._secret_rotary_interval * 24 * 60 * 60
        )

    def _encode(self, payload: dict, audience: str, secret: str) -> str:
        payload = payload.copy()
        now = datetime.now(UTC)
        payload.update({
            "exp": now + timedelta(days=self._token_expiry_days),
            "iat": now,
            "nbf": now,
            "iss": self._token_issuer,
            "aud": self._token_audiences.get(audience, audience)
        })
        return jwt.encode(
            payload, secret,
            headers={ "kid": self._current_key },
            algorithm=self._token_algorithm
        )

    def _decode(self, token: str, audience: str, secret: str) -> dict:
        return jwt.decode(
            token, secret,
            algorithms=[self._token_algorithm],
            issuer=self._token_issuer,
            audience=self._token_audiences.get(audience, audience),
            verify=True
        )

    def _check(self):
        if not self._current_key: raise FrameworkException("JWTManager not initialized.")

    def expand_fluid(self, fluid: "Fluid", *_, **__):
        if not EXT_SCHEDULING:
            raise FrameworkException("EXT_SCHEDULING is required for JWTManager to work.")
        if not EXT_CACHE:
            raise FrameworkException("EXT_CACHE is required for JWTManager to work.")

        self._secret_rotary_interval = fluid.config.get(
            "JWT_ROTARY_INTERVAL", self._secret_rotary_interval
        )
        self._secret_length = fluid.config.get(
            "JWT_SECRET_LENGTH", self._secret_length
        )

        from webfluid.core.ext import scheduler
        fluid.startup_hook(self._rotate_secret)
        scheduler.add_job(
            self._rotate_secret,
            IntervalTrigger(
                days=self._secret_rotary_interval,
                start_date=datetime.now(UTC)
            )
        )

        self._token_expiry_days = fluid.config.get("JWT_EXPIRY_DAYS", self._token_expiry_days)
        self._token_algorithm = fluid.config.get("JWT_ALGORITHM", self._token_algorithm)
        self._token_issuer = fluid.config.get("JWT_ISSUER", self._token_issuer)
        self._token_audiences = fluid.config.get("JWT_AUDIENCES", self._token_audiences)

    def encode(self, payload: dict, audience: str = "default") -> str:
        self._check()

        from webfluid.core.ext import cache
        secret = cache.get(f"jwt:{self._current_key}")
        return self._encode(payload, audience, secret)

    async def aencode(self, payload: dict, audience: str = "default") -> str:
        self._check()

        from webfluid.core.ext import cache
        secret = await cache.aget(f"jwt:{self._current_key}")
        return self._encode(payload, audience, secret)

    def decode(self, token: str, audience: str = "default") -> dict:
        self._check()

        from webfluid.core.ext import cache
        kid = jwt.get_unverified_header(token).get("kid", self._current_key)
        secret = cache.get(f"jwt:{kid}")
        return self._decode(token, audience, secret)

    async def adecode(self, token: str, audience: str = "default") -> dict:
        self._check()

        from webfluid.core.ext import cache
        kid = jwt.get_unverified_header(token).get("kid", self._current_key)
        secret = await cache.aget(f"jwt:{kid}")
        return self._decode(token, audience, secret)
