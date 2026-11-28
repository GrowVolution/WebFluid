from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from webfluid import Fluid

TRUSTED_PROXY: str

class TrustedProxyHeadersMiddleware(ProxyHeadersMiddleware): ...

def add(fluid: Fluid) -> None: ...
