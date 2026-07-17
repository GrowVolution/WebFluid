from fastapi.responses import HTMLResponse

from ..error import error_templates
from webfluid.core.context.fluid import FluidContext


def add_hook(fluid):
    @fluid.after_request
    async def after_request(response):
        r = FluidContext.current().request
        if "text/html" not in r.headers.get("accept", ""):
            return response

        template = error_templates.get(response.status_code)
        if template is None: return response

        return HTMLResponse(
            await fluid.render(template),
            status_code=response.status_code
        )
