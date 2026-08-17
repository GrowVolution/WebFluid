from datetime import datetime, UTC

from ..timestamping import timestamped
from webfluid.core.constants import DEBUG
from webfluid.core.context.fluid import FluidContext


def offline_url(fluid, endpoint, external, path_params):
    path = str(fluid.url_path_for(endpoint, **path_params))
    if not external: return path
    return f"{fluid.config['BASE_URL'].rstrip('/')}{path}"


def url_for(fluid):
    ctx = FluidContext.try_current()
    request = ctx.request if ctx is not None else None

    def wrapper(endpoint, **path_params):
        external = path_params.pop("external", False)

        if request is not None:
            url = request.url_for(endpoint, **path_params)
            result = str(url) if external else url.path
        else:
            result = offline_url(fluid, endpoint, external, path_params)

        if DEBUG and "static" in result:
            result = timestamped(
                result, datetime.now(UTC).timestamp()
            )

        return result
    return wrapper
