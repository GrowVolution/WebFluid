
__all__ = [
    "choice", "fixed_choice",
    "select", "checkbox", "text",
    "confirm", "password",

    "frontend_type", "frontend_framework",
    "use_typescript", "register_index", "use_alpine",
    "confirm_safe_id", "select_base", "additive_name",
    "version_format", "as_base", "extend", "description",
    "author", "email", "requirements", "database_uri",
    "additives", "redis_uri", "mail_username", "mail_password",
    "extensions", "features",

    "host", "port", "debug_mode", "menu",

    "ocean_token", "ocean_license_query", "ocean_confirm_overwrite",
    "ocean_confirm_overwrite_invalid", "ocean_confirm_waiver",
    "ocean_price", "ocean_maintainer", "ocean_license_choice"
]


def __getattr__(name):
    if name in {
        "choice", "fixed_choice",
        "select", "checkbox", "text",
        "confirm", "password"
    }:
        from . import main
        return getattr(main, name)

    if name in {
        "frontend_type", "frontend_framework",
        "use_typescript", "register_index", "use_alpine",
        "confirm_safe_id", "select_base", "additive_name",
        "version_format", "as_base", "extend", "description",
        "author", "email", "requirements", "database_uri",
        "additives", "redis_uri", "mail_username", "mail_password",
        "extensions", "features"
    }:
        from . import create
        return getattr(create, name)

    if name in {
        "host", "port", "debug_mode", "menu"
    }:
        from . import run
        return getattr(run, name)

    if name in {
        "ocean_token", "ocean_license_query", "ocean_confirm_overwrite",
        "ocean_confirm_overwrite_invalid", "ocean_confirm_waiver",
        "ocean_price", "ocean_maintainer", "ocean_license_choice"
    }:
        from . import ocean
        return getattr(ocean, name.replace("ocean_", ""))

    raise AttributeError(name)


def __dir__(): return sorted(__all__)
