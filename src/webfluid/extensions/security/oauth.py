from authlib.integrations.starlette_client import OAuth as StarletteClient
from typing import TYPE_CHECKING, Any

from webfluid.extensions.base import FluidExtension

if TYPE_CHECKING:
    from webfluid import Fluid


class OAuth(FluidExtension):
    def __init__(self, fluid: "Fluid | None" = None):
        self._client = StarletteClient()
        super().__init__(fluid)

    def __getattr__(self, name: str) -> Any | None:
        return getattr(self._client, name, None)

    def expand_fluid(self, fluid: "Fluid", *_, **__):
        clients = fluid.config.get("OAUTH_CLIENTS", {})
        for name, client in clients.items():
            self._client.register(name, **client)
