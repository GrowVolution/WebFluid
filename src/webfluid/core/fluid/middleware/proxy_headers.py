

def add(fluid):
    if not fluid.config["PROXY_FIX"]: return

    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
    fluid.add_middleware(
        ProxyHeadersMiddleware,
        trusted_hosts=fluid.config["PROXY_TRUSTED_HOSTS"]
    )
