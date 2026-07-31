import string, re

from webfluid.core.config import DefaultConfig

_codes = {
    "lower": "MIN_LOWER",
    "upper": "MIN_UPPER",
    "digits": "MIN_DIGITS",
    "special": "MIN_SPECIAL"
}

_policy = None


def validate_username(username):
    if not re.match(r"^[a-zA-Z0-9_-]{3,30}$", username):
        raise ValueError("INVALID_USERNAME")
    return username


class PasswordPolicy:
    def __init__(self, min_length, requirements):
        self.min_length = min_length
        self.requirements = requirements

    def _counts(self, password):
        counts = dict.fromkeys(_codes, 0)

        for c in password:
            if c.islower(): counts["lower"] += 1
            elif c.isupper(): counts["upper"] += 1
            elif c.isdigit(): counts["digits"] += 1
            elif c in string.punctuation: counts["special"] += 1

        return counts

    def validate(self, password):
        errors = []

        if len(password) < self.min_length:
            errors.append("MIN_LENGTH_%i" % self.min_length)

        counts = self._counts(password)
        for key, code in _codes.items():
            minimum = self.requirements.get(key, 1)
            if counts[key] < minimum:
                errors.append("%s_%i" % (code, minimum))

        if len(errors) > 0:
            exc = ValueError()
            exc.errors = errors
            raise exc

        return password


default_policy = PasswordPolicy(
    DefaultConfig.SECURITY_PASSWORD_MIN_LENGTH,
    DefaultConfig.SECURITY_PASSWORD_REQUIREMENTS
)


def set_policy(policy):
    global _policy
    _policy = policy


def validate_password(password):
    return (_policy or default_policy).validate(password)
