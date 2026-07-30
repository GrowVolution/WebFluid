import string, re

from webfluid.core.config import DefaultConfig
from webfluid.core.context import FluidContext


def validate_username(username):
    if not re.match(r"^[a-zA-Z0-9_-]{3,30}$", username):
        raise ValueError("INVALID_USERNAME")
    return username


def validate_password(password):
    min_len, requirements = FluidContext.get_ctx_data(
        DefaultConfig,
        "SECURITY_PASSWORD_MIN_LENGTH",
        "SECURITY_PASSWORD_REQUIREMENTS"
    )

    errors = []

    if len(password) < min_len:
        errors.append("MIN_LENGTH_%i" % min_len)

    lower = upper = digits = special = 0
    for c in password:
        if c.islower():
            lower += 1
        elif c.isupper():
            upper += 1
        elif c.isdigit():
            digits += 1
        elif c in string.punctuation:
            special += 1

    min_lower = requirements.get("lower", 1)
    if lower < min_lower:
        errors.append("MIN_LOWER_%i" % min_lower)

    min_upper = requirements.get("upper", 1)
    if upper < min_upper:
        errors.append("MIN_UPPER_%i" % min_upper)

    min_digits = requirements.get("digits", 1)
    if digits < min_digits:
        errors.append("MIN_DIGITS_%i" % min_digits)

    min_special = requirements.get("special", 1)
    if special < min_special:
        errors.append("MIN_SPECIAL_%i" % min_special)

    if len(errors) > 0:
        exc = ValueError()
        exc.errors = errors
        raise exc

    return password
