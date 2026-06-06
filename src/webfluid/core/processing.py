from fastapi import Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from pydantic import BaseModel
from datetime import datetime, UTC
from selectolax.lexbor import LexborHTMLParser
from typing import TYPE_CHECKING
import traceback

from webfluid.core.context import FluidContext
from webfluid.core.constants import FRAMEWORK_ID, EXT_BABEL, THEMES, DEBUG
from webfluid.extensions.babel.utils import get_locale, fake_t, fake_tn
from webfluid.utils.logging import factory as log_factory

if TYPE_CHECKING:
    from webfluid.core.fluid import Fluid


class Source(BaseModel):
    tag: str
    attrs: dict[str, str]
    text: str


class ServerConfig(BaseModel):
    base_url: str
    app_name: str
    app_version: str
    framework_id: str
    framework_version: str
    sources: list[Source]


_error_templates = {
    400: "errors/400.html",
    401: "errors/401.html",
    403: "errors/403.html",
    404: "errors/404.html",
    405: "errors/405.html",
    429: "errors/429.html",
    500: "errors/500.html",
    502: "errors/502.html",
    503: "errors/503.html"
}


def _timestamped(path: str) -> str:
    return path + f"?t={datetime.now(UTC).timestamp()}"


def setup_processing(fluid: "Fluid"):
    if not EXT_BABEL:
        fluid.jinja_env.add_extension("jinja2.ext.i18n")
        fluid.jinja_env.install_gettext_callables(
            fake_t, fake_tn, newstyle=True
        )
        lang = lambda: "en"
    else:
        lang = get_locale

    def theme():
        if not THEMES: return ""
        return fluid.get_theme()

    def url_for():
        try:
            ctx = FluidContext.current()
            if not ctx.request: return None
            fn = FluidContext.current().request.url_for
        except RuntimeError: return None

        def wrapper(endpoint: str, **path_params):
            external = path_params.pop("external", False)
            url = fn(endpoint, **path_params)

            if external: result = str(url)
            else: result = url.path

            if DEBUG and "static" in result:
                result = _timestamped(result)

            return result
        return wrapper

    fluid.context_processor(lambda: {
        "LANG": lang(),
        "YEAR": datetime.now(UTC).year,

        "id": FRAMEWORK_ID,
        "theme": theme(),
        "src": "\n\t".join(fluid.sources),
        "url_for": url_for()
    })

    @fluid.before_request
    def before_request():
        r = FluidContext.current().request
        agent = r.headers.get("user-agent", "unknown")
        log_factory.log(
            f"[Request] {r.method} {r.url.path} from {r.client.host} ({agent})"
        )

    @fluid.after_request
    async def after_request(response: Response):
        r = FluidContext.current().request
        if "text/html" not in r.headers.get("accept", ""):
            return response

        template = _error_templates.get(response.status_code)
        if template is None: return response

        return HTMLResponse(
            await fluid.render(template),
            status_code=response.status_code
        )

    @fluid.exception_handler(Exception)
    async def exception_handler(request: Request, exc: Exception):
        if isinstance(exc, (RequestValidationError, HTTPException)): raise
        log_factory.exception(exc, f"{request.method} {request.url.path}")

        if "text/html" not in request.headers.get("accept", ""):
            content = {
                "error": "Internal Server Error",
                "message": str(exc)
            }
            if DEBUG:
                content["type"] = type(exc).__name__
                content["method"] = request.method
                content["path"] = request.url.path
                content["traceback"] = traceback.format_exception(exc)
            return JSONResponse(content=content, status_code=500)

        async with FluidContext(fluid, request):
            if DEBUG:
                return HTMLResponse(
                    await fluid.render(
                        "errors/debug/500.html",
                        error_type=type(exc).__name__,
                        error=str(exc),
                        method=request.method,
                        path=request.url.path,
                        traceback="".join(traceback.format_exception(exc))
                    ),
                    status_code=500
                )

            return HTMLResponse(
                await fluid.render("errors/500.html"),
                status_code=500
            )

    @fluid.get("/server-config")
    async def config(request: Request):
        sources = []

        if THEMES:
            node = LexborHTMLParser(
                fluid.get_theme(), True
            ).root

            if DEBUG and "href" in node.attributes:
                node.attrs["href"] = _timestamped(node.attrs["href"])

            source = {
                "tag": node.tag,
                "attrs": node.attributes,
                "text": node.text()
            }
            sources.append(source)

        for src in fluid.sources:
            node = LexborHTMLParser(
                src, True
            ).root

            if DEBUG and "src" in node.attributes:
                node.attrs["src"] = _timestamped(node.attrs["src"])

            elif DEBUG and "href" in node.attributes:
                node.attrs["href"] = _timestamped(node.attrs["href"])

            source = {
                "tag": node.tag,
                "attrs": node.attributes,
                "text": node.text()
            }
            sources.append(source)

        from webfluid import version
        return {
            "base_url": str(request.base_url).rstrip("/"),
            "app_name": fluid.name,
            "app_version": fluid.config.get(
                "APP_CONFIG", {}
            ).get("version", "unknown"),
            "framework_id": FRAMEWORK_ID,
            "framework_version": str(version()).lstrip("v"),
            "sources": sources
        }
