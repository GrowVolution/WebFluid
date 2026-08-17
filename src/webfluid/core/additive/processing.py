from webfluid.core.context.fluid import FluidContext
from webfluid.core.constants import PROCESSING
from webfluid.core.processing.context.url_for import offline_url


def configure(additive):
    if not PROCESSING: return

    def url_for(endpoint, **path_params):
        ctx = FluidContext.try_current()
        if ctx is None: return None

        external = path_params.pop("external", False)
        endpoint = additive.unique_name(endpoint)

        if ctx.request is None:
            return offline_url(ctx.fluid, endpoint, external, path_params)

        url = ctx.request.url_for(endpoint, **path_params)
        if external: return str(url)
        return url.path

    additive.jinja_context["url_for"] = url_for
    additive.context_processor(lambda: additive.jinja_context)
