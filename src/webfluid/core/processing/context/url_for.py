from datetime import datetime, UTC

from ..timestamping import timestamped
from webfluid.core.constants import DEBUG
from webfluid.core.context.fluid import FluidContext


def url_for():
    ctx = FluidContext.try_current()
    if ctx is None or ctx.request is None: return None
    fn = ctx.request.url_for

    def wrapper(endpoint, **path_params):
        external = path_params.pop("external", False)
        url = fn(endpoint, **path_params)

        result = str(url) if external else url.path
        if DEBUG and "static" in result:
            result = timestamped(
                result, datetime.now(UTC).timestamp()
            )

        return result
    return wrapper
