from pydantic import BaseModel
from datetime import datetime, UTC

from webfluid import version
from webfluid.core.identity import FRAMEWORK_ID, IDENTITY_ROUTE


def add_route(fluid):
    @fluid.get(IDENTITY_ROUTE, response_model=FrameworkIdentity)
    def identity():
        return {
            "id": FRAMEWORK_ID,
            "version": str(version()),
            "timestamp": datetime.now(UTC).isoformat()
        }


class FrameworkIdentity(BaseModel):
    id: str
    version: str
    timestamp: str
