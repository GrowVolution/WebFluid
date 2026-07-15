from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


def add(fluid):
    if fluid.config.get("PROXY_FIX", False):
        fluid.add_middleware(
            ProxyHeadersMiddleware,
            trusted_hosts=fluid.config.get(
                "PROXY_TRUSTED_HOSTS", "127.0.0.1"
            )
        )
