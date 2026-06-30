from typing import Any
from pydantic import BaseModel
from selectolax.lexbor import LexborNode

from webfluid import Fluid

class FrameworkIdentity(BaseModel):
    id: str
    version: str
    timestamp: str

class UrlFor(BaseModel):
    endpoint: str
    path_params: dict[str, Any]
    external: bool = ...

_error_templates: dict[int, str]

def _timestamped(path: str, ts: float) -> str: ...
def _timestamped_node(src: str, ts: float) -> LexborNode: ...
def setup_processing(fluid: Fluid) -> None: ...
