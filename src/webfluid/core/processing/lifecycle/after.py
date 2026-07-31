from fastapi.responses import HTMLResponse

from ..error import error_templates
from webfluid.core.context.fluid import FluidContext


def install_error_pages(fluid):
    @fluid.after_request
    async def after_request(response):
        template = error_templates.get(response.status_code)
        if template is None: return response

        r = FluidContext.current().request
        if "text/html" not in r.headers.get("accept", ""):
            return response

        return HTMLResponse(
            await fluid.render(template),
            status_code=response.status_code
        )
