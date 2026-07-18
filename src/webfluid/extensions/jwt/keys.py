from webfluid.exceptions import FrameworkException


def _validated_key(key):
    if key is None:
        raise FrameworkException("JWTManager not initialized.")
    return key


def current_key(cache):
    key = cache.get("jwt:current")
    return _validated_key(key)


async def acurrent_key(cache):
    key = await cache.aget("jwt:current")
    return _validated_key(key)
