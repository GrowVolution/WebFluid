from authlib.integrations.base_client import MismatchingStateError
from authlib.integrations.starlette_client import OAuth
from fastapi import Request, Depends
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import json

_script = """<script>
    window.opener.postMessage({{
        status: "ok",
        provider: {provider},
    }}, {base_url})

    window.close()
</script>"""


def _local_path(target):
    if not isinstance(target, str) or not target.startswith("/"): return "/"
    if target[1:2] in ("/", "\\"): return "/"
    if "\\" in target or any(ord(char) < 0x20 or ord(char) == 0x7f for char in target): return "/"
    return target


def _script_value(value):
    return json.dumps(str(value)).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


class OAuthService:
    def __init__(self, clients):
        self._client = OAuth()
        self._allowed_providers = set()
        for name, client in clients.items():
            self._client.register(name, **client)
            self._allowed_providers.add(name)

        self.client = Depends(self._resolve_client())
        self.prepare_session = Depends(OAuthService._prepare_session)
        self.userinfo = Depends(self._userinfo())

    def _resolve_client(self):
        async def wrapped(provider):
            if provider not in self._allowed_providers:
                raise HTTPException(status_code=400, detail="UNKNOWN_PROVIDER")
            return self._client.create_client(provider)
        return wrapped

    def _userinfo(self):
        async def wrapped(request: Request, provider):
            if provider not in self._allowed_providers:
                raise HTTPException(status_code=400, detail="UNKNOWN_PROVIDER")

            error = request.query_params.get("error")
            if error: raise HTTPException(status_code=400, detail=error)

            try:
                client = self._client.create_client(provider)
                token = await client.authorize_access_token(request)
            except MismatchingStateError:
                raise HTTPException(status_code=400, detail="INVALID_STATE")

            userinfo = token.get("userinfo")
            if not userinfo:
                userinfo = await client.userinfo(token=token)

            return userinfo
        return wrapped

    @staticmethod
    async def _prepare_session(request: Request):
        device = request.query_params.get("device", "mobile")
        if device not in ("mobile", "desktop"):
            raise HTTPException(status_code=400, detail="INVALID_DEVICE")

        if device == "mobile":
            request.session["redirect_path"] = _local_path(
                request.query_params.get("redirect", "/")
            )

        request.session["device"] = device

    def register_provider(self, name, client):
        self._client.register(name, **client)
        self._allowed_providers.add(name)

    def unregister_provider(self, name):
        self._client.unregister(name)
        self._allowed_providers.remove(name)

    @staticmethod
    def authorize_response(request, provider, device, csrf=None):
        if device == "desktop":
            response = HTMLResponse(_script.format(
                provider=_script_value(provider),
                base_url=_script_value(str(request.base_url).rstrip("/"))
            ))

        else:
            response = RedirectResponse(
                _local_path(request.session.pop("redirect_path", "/"))
            )

        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        if csrf is not None:
            for header in csrf.raw_headers:
                if header[0].lower() == b"set-cookie":
                    response.raw_headers.append(header)

        return response
