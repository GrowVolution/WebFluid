from .main import password, text, confirm, select, fixed_choice
from webfluid.core.identity import HUB_NAME

token = password(
    f"Paste your {HUB_NAME} JWT token:"
)

license_query = text(
    "Search for a license (e.g. MIT, Apache-2.0):",
    default=""
)


def _valid_license_value(value):
    value = value.strip()
    if not value: return "This field is required."
    if len(value) > 300: return "Use at most 300 characters."
    if any(ord(char) < 32 or ord(char) == 127 for char in value): return "Use a single line."
    return True


def _valid_price(value, required):
    value = value.strip()
    if not value:
        return True if not required else "A price is required for extensions."
    try: price = float(value)
    except ValueError: return "Enter a number like 9.99."
    if price <= 0: return "Price must be greater than 0."
    return True


def confirm_overwrite(username, days):
    return confirm(
        f"You are already logged in as {username}. Your token is valid for "
        f"{days} more days. Do you really want to overwrite it?",
        default=False
    )


def confirm_overwrite_invalid():
    return confirm(
        "Your existing token could not be validated. "
        "Do you want to replace it?",
        default=True
    )


def confirm_waiver(statement):
    return confirm(statement, default=False)


def confirm_release(package_id, version, security):
    kind = "security release" if security else "release"
    return confirm(f"'{package_id}' is published already. Upload version {version} as a new {kind}?", default=True)


def price(required):
    message = "Price in € (required):" if required \
        else "Price in € (empty for OSS/free):"
    return text(
        message,
        default="",
        validate=lambda value: _valid_price(value, required)
    )


def maintainer(options):
    return select(
        "Publish as:",
        choices=[fixed_choice(label, value) for label, value in options]
    )


def license_value(label, default):
    return text(f"{label}:", default=default, validate=_valid_license_value)


def license_choice(matches):
    choices = [
        fixed_choice(
            f"{match['license_id']} — {match['name']}"
            f"{' (OSI)' if match.get('osi_approved') else ''}",
            match["license_id"]
        )
        for match in matches
    ]
    choices.append(fixed_choice("🔁  Search again", "__search__"))
    return select(
        "Select a license:",
        choices=choices
    )
