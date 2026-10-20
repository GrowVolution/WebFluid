from fastapi.responses import HTMLResponse

from ..error import error_templates
from webfluid.core.context.fluid import FluidContext

_REPLACED_HEADERS = {b"content-length", b"content-type", b"content-encoding", b"transfer-encoding"}


def _error_page(response, content):
    page = HTMLResponse(content, status_code=response.status_code)
    page.raw_headers = [
        header for header in response.raw_headers if header[0].lower() not in _REPLACED_HEADERS
    ] + page.raw_headers
    return page


def install_error_pages(fluid):
    @fluid.after_request
    async def after_request(response):
        template = error_templates.get(response.status_code)
        if template is None: return response

        r = FluidContext.current().request
        if "text/html" not in r.headers.get("accept", ""):
            return response

        return _error_page(response, await fluid.render(template))
