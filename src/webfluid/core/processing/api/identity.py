from pydantic import BaseModel
from datetime import datetime, UTC

from webfluid import version
from webfluid.core.constants import FRAMEWORK_ID


class FrameworkIdentity(BaseModel):
    id: str
    version: str
    timestamp: str


def add_route(fluid):
    @fluid.get("/wf-identity", response_model=FrameworkIdentity)
    def identity():
        return {
            "id": FRAMEWORK_ID,
            "version": str(version()),
            "timestamp": datetime.now(UTC).isoformat()
        }
