from starlette.datastructures import URLPath
from starlette.routing import BaseRoute
from typing import Any

from webfluid import Fluid

class Routes:
    fluid: Fluid
    _index: dict[str, list[BaseRoute]]
    _count: int
    def __init__(self, fluid: Fluid) -> None: ...
    def _build(self) -> None: ...
    def url_path_for(self, name: str, **path_params: Any) -> URLPath: ...
