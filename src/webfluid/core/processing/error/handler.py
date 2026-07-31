from fastapi import HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
import traceback

from webfluid.core.constants import DEBUG
from webfluid.core.context.fluid import FluidContext
from webfluid.utils.logging import factory as log_factory


def install_error_handler(fluid):
    @fluid.exception_handler(Exception)
    async def exception_handler(request, exc):
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
