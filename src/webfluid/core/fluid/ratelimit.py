

def _disabled(*_, **__):
    return lambda fn: fn


class Limiter:
    def __init__(self, fluid):
        self.enabled = fluid.config["RATELIMIT_ENABLED"]
        if not self.enabled: return

        from slowapi import Limiter as _Limiter, _rate_limit_exceeded_handler
        from slowapi.util import get_remote_address
        from slowapi.errors import RateLimitExceeded

        self.limiter = _Limiter(
            key_func=get_remote_address,
            default_limits=fluid.config["RATELIMIT_DEFAULT"],
            storage_uri=fluid.config["RATELIMIT_STORAGE_URI"]
        )
        fluid.state.limiter = self.limiter
        fluid.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @property
    def limit(self):
        if self.enabled: return self.limiter.limit
        return _disabled
