from webfluid.cli.questions.main import (
    choice as choice,
    fixed_choice as fixed_choice,
    select as select,
    checkbox as checkbox,
    text as text,
    confirm as confirm,
    password as password,
)
from webfluid.cli.questions.create import (
    frontend_type as frontend_type,
    frontend_framework as frontend_framework,
    use_typescript as use_typescript,
    register_index as register_index,
    use_alpine as use_alpine,
    confirm_safe_id as confirm_safe_id,
    select_base as select_base,
    additive_name as additive_name,
    version_format as version_format,
    as_base as as_base,
    extend as extend,
    description as description,
    author as author,
    email as email,
    requirements as requirements,
    database_uri as database_uri,
    additives as additives,
    redis_uri as redis_uri,
    mail_username as mail_username,
    mail_password as mail_password,
    extensions as extensions,
    features as features,
)
from webfluid.cli.questions.run import (
    host as host,
    port as port,
    debug_mode as debug_mode,
    menu as menu,
)
from webfluid.cli.questions.ocean import (
    token as ocean_token,
    license_query as ocean_license_query,
    confirm_overwrite as ocean_confirm_overwrite,
    confirm_overwrite_invalid as ocean_confirm_overwrite_invalid,
    confirm_waiver as ocean_confirm_waiver,
    price as ocean_price,
    maintainer as ocean_maintainer,
    license_choice as ocean_license_choice,
)

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
    "ocean_price", "ocean_maintainer", "ocean_license_choice",
]
