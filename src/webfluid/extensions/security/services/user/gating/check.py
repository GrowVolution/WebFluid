from . import requirements
from webfluid.utils.core import async_result


async def check_requirement(user, r):
    requirement = r.get("requirement")
    if not requirement or not isinstance(requirement, str):
        raise ValueError("Invalid requirement format.")

    if requirement == "is_authenticated":
        return user is not None

    if requirement not in {
        "is_admin", "has_2fa", "has_roles", "has_any_role",
        "has_permissions", "has_any_permission"
    }:
        raise ValueError("Invalid requirement format: Invalid requirement.")

    if await requirements.is_admin(user): return True

    param = None

    if requirement in {
        "has_roles", "has_any_role"
    } and ("roles" not in r or not isinstance(r["roles"], list)):
        raise ValueError("Invalid requirement format: Invalid or missing 'roles' field.")

    elif requirement in {
        "has_roles", "has_any_role"
    }:
        param = r["roles"]

    if requirement in {
        "has_permissions", "has_any_permission"
    } and ("permissions" not in r or not isinstance(r["permissions"], list)):
        raise ValueError("Invalid requirement format: Invalid or missing 'permissions' field.")

    elif requirement in {
        "has_permissions", "has_any_permission"
    }:
        param = r["permissions"]

    check = getattr(requirements, requirement)
    result = check(user, param) if param else check(user)
    return await async_result(result)
