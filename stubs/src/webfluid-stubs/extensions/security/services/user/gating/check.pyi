from typing import Any

from webfluid.extensions.security.models.user import User

async def check_requirement(user: User | None, r: dict[str, Any]) -> bool: ...
