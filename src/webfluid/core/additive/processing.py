from webfluid.core.context.fluid import FluidContext
from webfluid.core.constants import PROCESSING


def configure(additive):
    if PROCESSING:
        def url_for(endpoint, **path_params):
            try:
                ctx = FluidContext.current()
                if not ctx.request: return None
                fn = FluidContext.current().request.url_for
            except RuntimeError: return None

            external = path_params.pop("external", False)
            url = fn(additive.unique_name(endpoint), **path_params)
            if external: return str(url)
            return url.path

        additive.jinja_context["url_for"] = url_for
        additive.context_processor(lambda: additive.jinja_context)
