from webfluid.core.context.fluid import FluidContext
from webfluid.utils.logging import factory as log_factory


def install_request_logger(fluid):
    @fluid.before_request
    def before_request():
        r = FluidContext.current().request
        agent = r.headers.get("user-agent", "unknown")
        log_factory.log(
            f"[Request] {r.method} {r.url.path} from {r.client.host} ({agent})"
        )
