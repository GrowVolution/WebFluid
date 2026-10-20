from fastapi import Request, Response
from fastapi.responses import FileResponse
from mimetypes import guess_type

from .dev import dev_server, dev_prefix
from webfluid.core.constants import DEBUG, FRAMEWORK_STATIC

_static = FRAMEWORK_STATIC.lstrip("/")


def contained(root, *parts):
    try: resolved = root.joinpath(*parts).resolve()
    except (OSError, ValueError): return None

    if not resolved.is_relative_to(root): return None
    return resolved if resolved.is_file() else None


def _asset_path(project_root, namespace, path):
    candidates = (
        ((namespace, path), (namespace, "public", path)) if DEBUG
        else ((namespace, "dist", path),)
    )
    for parts in candidates:
        if contained(project_root, *parts): return "/".join(parts)
    return None


def asset_catch(project_root, namespaces):
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
            if vite_ns not in namespaces: return Response(status_code=404)

            final_path = _asset_path(project_root, vite_ns, path)
            if final_path is None: return Response(status_code=404)

        if DEBUG:
            from webfluid.utils.core import get_proxy
            proxy = get_proxy(
                dev_server,
                prefix=dev_prefix,
                pass_prefix=True
            )

            return await proxy(request, final_path)

        file = contained(project_root, final_path)
        if file is None: return Response(status_code=404)

        return FileResponse(
            file,
            filename=file.name,
            media_type=guess_type(file)[0]
                       or "application/octet-stream"
        )

    return wrapped
