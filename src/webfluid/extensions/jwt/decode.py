import jwt

from .keys import current_key, acurrent_key


class Decoder:
    def __init__(self, jwt_manager):
        self._jwt_manager = jwt_manager

    def _decode(self, token, audience, secret, cache):
        jwt_manager = self._jwt_manager
        token = jwt.decode(
            token, secret,
            algorithms=[jwt_manager._token_algorithm],
            issuer=jwt_manager._token_issuer,
            audience=jwt_manager._token_audiences.get(audience, audience),
            verify=True
        )
        if "jti" in token:
            revoked = cache.get(f"jwt:revoked:{token['jti']}")
            if revoked: raise jwt.InvalidTokenError("Token revoked.")
        return token

    def decode(self, token, audience="default"):
        from webfluid.core.ext import cache
        key = current_key(cache)
        kid = jwt.get_unverified_header(token).get("kid", key)
        secret = cache.get(f"jwt:{kid}")
        return self._decode(token, audience, secret, cache)

    async def adecode(self, token, audience="default"):
        from webfluid.core.ext import cache
        key = await acurrent_key(cache)
        kid = jwt.get_unverified_header(token).get("kid", key)
        secret = await cache.aget(f"jwt:{kid}")
        return self._decode(token, audience, secret, cache)
