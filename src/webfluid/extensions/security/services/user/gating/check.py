from . import requirements
from webfluid.utils.core import async_result

_PARAMETERS = {
    "has_roles": "roles", "has_any_role": "roles",
    "has_permissions": "permissions", "has_any_permission": "permissions"
}
_REQUIREMENTS = {"is_admin", "has_2fa", *_PARAMETERS}


async def check_requirement(user, r):
    requirement = r.get("requirement")
    if not requirement or not isinstance(requirement, str):
        raise ValueError("Invalid requirement format.")

    if requirement == "is_authenticated":
        return user is not None

    if requirement not in _REQUIREMENTS:
        raise ValueError("Invalid requirement format: Invalid requirement.")

    field = _PARAMETERS.get(requirement)
    param = r.get(field) if field else None
    if field and (not isinstance(param, list) or not param):
        raise ValueError(f"Invalid requirement format: Invalid or missing '{field}' field.")

    if user is None: return False
    if await requirements.is_admin(user): return True

    check = getattr(requirements, requirement)
    result = check(user) if field is None else check(user, param)
    return await async_result(result)
