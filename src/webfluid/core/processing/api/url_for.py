from fastapi import HTTPException, Request
from starlette.routing import NoMatchFound
from datetime import datetime, UTC

from .schemas import UrlFor
from webfluid.core.constants import DEBUG


def add_route(fluid):
    # TODO(1.1): move under the framework prefix like IDENTITY_ROUTE; the bare
    # path can collide with app routes. Renaming needs a deprecation window.
    from ..timestamping import timestamped

    @fluid.post("/url-for")
    async def url_for(request: Request, data: UrlFor):
        try: url = request.url_for(data.endpoint, **data.path_params)
        except NoMatchFound:
            raise HTTPException(status_code=404, detail="UNKNOWN_ENDPOINT")

        result = str(url) if data.external else url.path
        return {
            "url": timestamped(
                result, datetime.now(UTC).timestamp()
            ) if DEBUG else result
        }
