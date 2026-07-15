from slowapi import Limiter as _Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_ipaddr
from slowapi.errors import RateLimitExceeded


class Limiter:
    def __init__(self, fluid):
        self.enabled = False

        if fluid.config.get("RATELIMIT_ENABLED", True):
            self.limiter = _Limiter(
                key_func=get_ipaddr,
                default_limits=fluid.config.get(
                    "RATELIMIT_DEFAULT", ["500/day", "100/hour"]
                ),
                storage_uri=fluid.config.get(
                    "RATELIMIT_STORAGE_URI", "redis://localhost:6379/1"
                ),
            )
            fluid.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
            self.enabled = True

    @property
    def limit(self):
        if self.enabled: return self.limiter.limit
        return lambda *_, **__: lambda fn: fn
