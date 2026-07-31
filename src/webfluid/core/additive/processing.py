from webfluid.core.context.fluid import FluidContext
from webfluid.core.constants import PROCESSING


def configure(additive):
    if not PROCESSING: return

    def url_for(endpoint, **path_params):
        ctx = FluidContext.try_current()
        if ctx is None or ctx.request is None: return None

        external = path_params.pop("external", False)
        url = ctx.request.url_for(additive.unique_name(endpoint), **path_params)
        if external: return str(url)
        return url.path

    additive.jinja_context["url_for"] = url_for
    additive.context_processor(lambda: additive.jinja_context)
