from typing import Any
from pydantic import BaseModel

from webfluid.core.fluid import Fluid

class UrlFor(BaseModel):
    endpoint: str
    path_params: dict[str, Any]
    external: bool = ...

def add_route(fluid: Fluid) -> None: ...
