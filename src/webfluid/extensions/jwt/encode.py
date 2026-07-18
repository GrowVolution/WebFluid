from datetime import datetime, timedelta, UTC
import jwt

from .keys import current_key, acurrent_key


class Encoder:
    def __init__(self, jwt_manager):
        self._jwt_manager = jwt_manager

    def _encode(self, payload, audience, secret, expire, kid):
        jwt_manager = self._jwt_manager
        payload = payload.copy()
        now = datetime.now(UTC)
        payload.update({
            "exp": now + timedelta(days=expire or jwt_manager._token_expiry_days),
            "iat": now,
            "nbf": now,
            "iss": jwt_manager._token_issuer,
            "aud": jwt_manager._token_audiences.get(audience, audience)
        })
        return jwt.encode(
            payload, secret,
            headers={ "kid": kid },
            algorithm=jwt_manager._token_algorithm
        )

    def encode(self, payload, audience="default", expire=None):
        from webfluid.core.ext import cache
        key = current_key(cache)
        secret = cache.get(f"jwt:{key}")
        return self._encode(payload, audience, secret, expire, key)

    async def aencode(self, payload, audience="default", expire=None):
        from webfluid.core.ext import cache
        key = await acurrent_key(cache)
        secret = await cache.aget(f"jwt:{key}")
        return self._encode(payload, audience, secret, expire, key)
