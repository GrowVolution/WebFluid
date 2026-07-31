from fastapi import Request, Response
from fastapi.responses import FileResponse
from mimetypes import guess_type

from .dev import dev_server, dev_prefix
from webfluid.core.constants import DEBUG, FRAMEWORK_STATIC

_static = FRAMEWORK_STATIC.lstrip("/")


def asset_catch(project_root):
    async def wrapped(request: Request, path: str):
        if path.startswith(("api", _static)) or "/frontend" in path:
            return Response(status_code=404)

        if "." not in path:
            return Response(status_code=404)

        if path.startswith("."):
            if not DEBUG:
                return Response(status_code=404)
            final_path = path
        else:
            vite_ns = request.cookies.get("vite_ns")
            if vite_ns is None: return Response(status_code=404)

            if (project_root / vite_ns / path).exists():
                final_path = f"{vite_ns}/{path}"

            elif (project_root / vite_ns / "public" / path).exists():
                final_path = f"{vite_ns}/public/{path}"

            else: return Response(status_code=404)

        if DEBUG:
            from webfluid.utils.core import get_proxy
            proxy = get_proxy(
                dev_server,
                prefix=dev_prefix,
                pass_prefix=True
            )

            return await proxy(request, final_path)

        file = project_root / final_path
        return FileResponse(
            file,
            filename=file.name,
            media_type=guess_type(file)[0]
                       or "application/octet-stream"
        )

    return wrapped
