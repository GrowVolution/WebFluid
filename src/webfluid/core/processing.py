from fastapi import Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from pydantic import BaseModel
from datetime import datetime, UTC
from selectolax.lexbor import LexborHTMLParser
from typing import TYPE_CHECKING

from webfluid.core.context import FluidContext
from webfluid.core.constants import APP_STATIC, WF_STATIC, EXT_BABEL, THEMES
from webfluid.extensions.utils.babel import get_locale, fake_t, fake_tn
from webfluid.utils.logging import factory as log_factory
from webfluid.exceptions import FrameworkException

if TYPE_CHECKING:
    from webfluid.core.fluid import Fluid


class Source(BaseModel):
    tag: str
    attrs: dict[str, str]
    text: str


class StaticPaths(BaseModel):
    app: str
    framework: str


class ServerConfig(BaseModel):
    base_url: str
    app_name: str
    app_version: str
    sources: list[Source]
    static_paths: StaticPaths


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
        try: return FluidContext.current().request.url_for
        except RuntimeError: return None

    fluid.context_processor(lambda: {
        **fluid.jinja_context,

        "LANG": lang(),
        "YEAR": datetime.now(UTC).year,

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
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type: return response

        if response.status_code == 403:
            return HTMLResponse(
                await fluid.render("errors/403.html"),
                status_code=403
            )

        if response.status_code == 404:
            return HTMLResponse(
                await fluid.render("errors/404.html"),
                status_code=404
            )

        return response

    @fluid.exception_handler(Exception)
    async def exception_handler(request: Request, exc: Exception):
        if isinstance(exc, (RequestValidationError, HTTPException)): raise
        log_factory.exception(exc, f"{request.method} {request.url.path}")

        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            return JSONResponse(
                content={
                    "error": "Internal Server Error",
                    "message": str(exc)
                },
                status_code=500
            )

        async with FluidContext(fluid, request):
            return HTMLResponse(
                await fluid.render("errors/500.html", error=str(exc)),
                status_code=500
            )

    @fluid.get("/server-config")
    async def config(request: Request):
        sources = []

        if THEMES:
            node = LexborHTMLParser(
                fluid.get_theme(), True
            ).root
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
            source = {
                "tag": node.tag,
                "attrs": node.attributes,
                "text": node.text()
            }
            sources.append(source)

        return {
            "base_url": str(request.base_url).rstrip("/"),
            "app_name": fluid.name,
            "app_version": fluid.config.get(
                "APP_CONFIG", {}
            ).get("version", "unknown"),
            "sources": sources,
            "static_paths": {
                "app": APP_STATIC,
                "framework": WF_STATIC
            }
        }

    if THEMES:
        @fluid.post("/set-theme")
        async def set_theme(request: Request):
            data = await request.json()
            if "theme" not in data:
                raise HTTPException(status_code=400, detail="Theme is required.")

            try: fluid.set_theme(request, data["theme"])
            except FrameworkException as e:
                raise HTTPException(status_code=400, detail=str(e))

            return { "status": "ok" }
