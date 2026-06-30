from fastapi import Request, Depends
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.exceptions import HTTPException
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client import MismatchingStateError


class OAuthService:
    def __init__(self, clients: dict):
        self._client = OAuth()
        self._allowed_providers = set()
        for name, client in clients.items():
            self._client.register(name, **client)
            self._allowed_providers.add(name)

        self.client = Depends(self._resolve_client())
        self.prepare_session = Depends(OAuthService._prepare_session)
        self.userinfo = Depends(self._userinfo())

    def _resolve_client(self):
        async def wrapped(provider: str):
            if provider not in self._allowed_providers:
                raise HTTPException(status_code=400, detail="UNKNOWN_PROVIDER")
            return self._client.create_client(provider)
        return wrapped

    def _userinfo(self):
        async def wrapped(request: Request, provider: str):
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

    def register_provider(self, name: str, client: dict):
        self._client.register(name, **client)
        self._allowed_providers.add(name)

    def unregister_provider(self, name: str):
        self._client.unregister(name)
        self._allowed_providers.remove(name)

    @staticmethod
    async def _prepare_session(request: Request):
        device = request.query_params.get("device", "mobile")
        if device not in ("mobile", "desktop"):
            raise HTTPException(status_code=400, detail="INVALID_DEVICE")

        if device == "mobile":
            redirect_path = request.query_params.get("redirect", "/")
            request.session["redirect_path"] = redirect_path

        request.session["device"] = device

    @staticmethod
    def authorize_response(request: Request, provider: str, device: str, csrf=None):
        if device == "desktop":
            response = HTMLResponse(f"""<script>
    window.opener.postMessage({{
        status: "ok",
        provider: "{provider}",
    }}, "{ str(request.base_url).rstrip("/") }")

    window.close()
</script>""")

        else:
            response = RedirectResponse(
                request.session.pop("redirect_path", "/")
            )

        if csrf is not None:
            for header in csrf.raw_headers:
                if header[0].lower() == b"set-cookie":
                    response.raw_headers.append(header)

        return response
