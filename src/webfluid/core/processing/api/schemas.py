from pydantic import BaseModel
from typing import Any


class FrameworkIdentity(BaseModel):
    id: str
    version: str
    timestamp: str


class UrlFor(BaseModel):
    endpoint: str
    path_params: dict[str, Any]
    external: bool = False
