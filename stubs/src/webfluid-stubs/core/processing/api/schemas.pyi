from typing import Any
from pydantic import BaseModel

class FrameworkIdentity(BaseModel):
    id: str
    version: str
    timestamp: str

class UrlFor(BaseModel):
    endpoint: str
    path_params: dict[str, Any]
    external: bool = ...
