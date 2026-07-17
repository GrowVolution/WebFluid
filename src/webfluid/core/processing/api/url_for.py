from pydantic import BaseModel
from fastapi import Request
from datetime import datetime, UTC
from typing import Any

from webfluid.core.constants import DEBUG


class UrlFor(BaseModel):
    endpoint: str
    path_params: dict[str, Any]
    external: bool = False


def add_route(fluid):
    from ..timestamping import timestamped

    @fluid.post("/url-for")
    async def url_for(request: Request, data: UrlFor):
        url = request.url_for(data.endpoint, **data.path_params)
        result = str(url) if data.external else url.path
        return {
            "url": timestamped(
                result, datetime.now(UTC).timestamp()
            ) if DEBUG else result
        }
