from webfluid.core.context.fluid import FluidContext
from webfluid.utils.logging import factory as log_factory


def _field(value: str, limit: int = 256) -> str:
    return "".join(char if char.isprintable() else "?" for char in value[:limit])


def install_request_logger(fluid):
    @fluid.before_request
    def before_request():
        r = FluidContext.current().request
        parts = ["[Request]", _field(r.method)]
        if fluid.config["REQUEST_LOG_PATH"]: parts.append(_field(r.url.path))
        if fluid.config["REQUEST_LOG_CLIENT"]:
            parts.extend(("from", _field(r.client.host if r.client else "unknown")))
        if fluid.config["REQUEST_LOG_USER_AGENT"]:
            parts.append(f"({_field(r.headers.get('user-agent', 'unknown'))})")
        log_factory.log(" ".join(parts))
