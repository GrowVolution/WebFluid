from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse

_script: str


class OAuthService:
    client: Any
    prepare_session: Any
    userinfo: Any

    def __init__(self, clients: dict[str, Any]) -> None: ...
    def _resolve_client(self) -> Callable[..., Any]: ...
    def _userinfo(self) -> Callable[..., Any]: ...
    def register_provider(self, name: str, client: dict[str, Any]) -> None: ...
    def unregister_provider(self, name: str) -> None: ...
    @staticmethod
    async def _prepare_session(request: Request) -> None: ...
    @staticmethod
    def authorize_response(
        request: Request, provider: str, device: str,
        csrf: JSONResponse | None = None,
    ) -> HTMLResponse | RedirectResponse: ...
