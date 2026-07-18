from typing import Any

from webfluid.extensions.events.queries import Queries

async def request(
    queries: Queries, msg: dict[str, Any], res: dict[str, Any]
) -> dict[str, Any]: ...
