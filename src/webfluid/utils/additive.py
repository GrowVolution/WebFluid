from functools import wraps

from webfluid.utils import safe_string, enabled
from webfluid.utils.logging import factory as log_factory


def id_check(additive_id: str) -> tuple[bool, str]:
    safe_id = safe_string(additive_id)
    if additive_id != safe_id:
        return False, f"Invalid id format '{additive_id}'. Try '{safe_id}' for example."
    return True, additive_id


def version_check(v: str) -> tuple[bool, str]:
    version_str = v.lower().strip()
    if not version_str:
        return False, "Additive version not defined."

    first_char_invalid = False
    try:
        int(version_str[0])
    except ValueError:
        first_char_invalid = True

    if  first_char_invalid \
            or (" " in version_str and not (
            version_str.endswith("alpha")
            or version_str.endswith("beta")
            or version_str.endswith("rc")
    )):
        return False, "Invalid version string format."

    try:
        v_numbers = version_str.split(" ")[0].split(".")
        if len(v_numbers) > 3:
            return False, "Too many version numbers."

        for v_number in v_numbers:
            int(v_number)
    except ValueError:
        return False, "Invalid version numbers."

    return True, version_str


def type_check(t: str) -> tuple[bool, str]:
    if t not in ("base", "default"):
        return False, f"Invalid type string '{t}'."
    return True, t


def require_extensions(*extensions):
    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            for ext in extensions:
                if not isinstance(ext, str):
                    log_factory.warn(f"Invalid extension '{ext}'.")
                    continue

                if not enabled(f"EXT_{ext.upper()}"):
                    raise RuntimeError(f"Extension '{ext}' is not enabled.")
            return func(*args, **kwargs)

        return wrapper
    return decorator
