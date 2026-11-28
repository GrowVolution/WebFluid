from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

TRUSTED_PROXY = "webfluid.trusted_proxy"


class TrustedProxyHeadersMiddleware(ProxyHeadersMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            client = scope.get("client")
            scope[TRUSTED_PROXY] = (client[0] if client else None) in self.trusted_hosts
        return await super().__call__(scope, receive, send)


def add(fluid):
    if not fluid.config["PROXY_FIX"]: return

    fluid.add_middleware(
        TrustedProxyHeadersMiddleware,
        trusted_hosts=fluid.config["PROXY_TRUSTED_HOSTS"]
    )
