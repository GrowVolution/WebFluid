from pydantic import BaseModel

from webfluid.core.fluid import Fluid

class FrameworkIdentity(BaseModel):
    id: str
    version: str
    timestamp: str

def add_route(fluid: Fluid) -> None: ...
