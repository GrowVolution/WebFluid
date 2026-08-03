import jwt

from .keys import current_key, acurrent_key


class Decoder:
    def __init__(self, config):
        self._config = config

    def _payload(self, token, audience, secret):
        if secret is None:
            raise jwt.InvalidTokenError("Unknown key id.")

        return jwt.decode(
            token, secret,
            algorithms=[self._config.algorithm],
            issuer=self._config.issuer,
            audience=self._config.audience(audience),
            verify=True
        )

    def _kid(self, token):
        return jwt.get_unverified_header(token).get("kid")

    def decode(self, token, audience="default"):
        from webfluid.core.ext import cache

        kid = self._kid(token) or current_key(cache)
        payload = self._payload(token, audience, cache.get(f"jwt:{kid}"))

        if "jti" in payload and cache.get(f"jwt:revoked:{payload['jti']}"):
            raise jwt.InvalidTokenError("Token revoked.")

        return payload

    async def adecode(self, token, audience="default"):
        from webfluid.core.ext import cache

        kid = self._kid(token) or await acurrent_key(cache)
        payload = self._payload(token, audience, await cache.aget(f"jwt:{kid}"))

        if "jti" in payload and await cache.aget(f"jwt:revoked:{payload['jti']}"):
            raise jwt.InvalidTokenError("Token revoked.")

        return payload
