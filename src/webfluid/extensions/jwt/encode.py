from datetime import datetime, timedelta, UTC
import jwt

from .keys import current_key, acurrent_key


class Encoder:
    def __init__(self, config):
        self._config = config

    def _encode(self, payload, audience, secret, expire, kid):
        payload = payload.copy()
        now = datetime.now(UTC)
        payload.update({
            "exp": now + timedelta(days=expire or self._config.expiry_days),
            "iat": now,
            "nbf": now,
            "iss": self._config.issuer,
            "aud": self._config.audience(audience)
        })
        return jwt.encode(
            payload, secret,
            headers={ "kid": kid },
            algorithm=self._config.algorithm
        )

    def encode(self, payload, audience="default", expire=None):
        from webfluid.core.ext import cache
        key = current_key(cache)
        return self._encode(payload, audience, cache.get(f"jwt:{key}"), expire, key)

    async def aencode(self, payload, audience="default", expire=None):
        from webfluid.core.ext import cache
        key = await acurrent_key(cache)
        return self._encode(
            payload, audience, await cache.aget(f"jwt:{key}"), expire, key
        )
