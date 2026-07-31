from pathlib import Path
import questionary

from .main import (
    select, confirm, checkbox, text,
    choice, fixed_choice
)

frontend_type = select(
    "Select your frontend type:",
    choices=[
        choice("🚫  None", "none"),
        choice("</> HTMX", "htmx"),
        choice("⚡  Vite", "vite"),
    ],
    default="none"
)

frontend_framework = select(
    "Select your frontend framework:",
    choices=[
        choice("🚫  None", "none"),
        choice("⚛️  React", "react"),
        choice("🟢  Vue", "vue"),
        choice("🔥  Svelte", "svelte"),
        choice("◆  Solid", "solid"),
        choice("📦  Preact", "preact"),
        choice("💡  Lit", "lit"),
        choice("⚡  Qwik", "qwik"),
    ],
    default="none"
)

use_typescript = confirm(
    "Do you want to use TypeScript?",
    default=False
)

register_index = confirm(
    "Automatically register the Vite index page on startup?",
    default=True
)

use_alpine = confirm(
    "Do you want to use AlpineJS?",
    default=False
)

#-------------- additive manifest-----------------#


def confirm_safe_id(given, suggestion):
    return confirm(
        f"Invalid id format '{given}'. Continue with '{suggestion}' instead?",
        default=True
    ).ask()


def select_base():
    from webfluid.utils.additives import installed_bases
    bases = installed_bases(Path.cwd() / "additives")
    if len(bases) == 0:
        raise ValueError("There are no base additives installed.")

    choices = [
        choice(f"<{base_id} {version}>", base_id)
        for base_id, version, _ in bases
    ]
    return select(
        "Select your base additive:",
        choices=choices,
        default=choices[0]
    ).ask()


def additive_name(additive_id):
    parts = additive_id.split("_")
    for i, part in enumerate(parts):
        parts[i] = part.capitalize()

    default = " ".join(parts)
    return text(
        "Enter your additive name:",
        default=default
    ).ask()


version_format = select(
    "Select a version format:",
    choices=[
        "1",
        "1.0",
        "1.0.0"
    ],
    default="1.0"
)

as_base = confirm(
    "Do you want to create a base additive?",
    default=False
)

extend = confirm(
    "Do you want to extend an existing additive?",
    default=False
)

description = text(
    "Describe your additive:",
    default=""
)

author = text(
    "Enter your name or nickname:",
    default=""
)

email = text(
    "Enter your email address:",
    default=""
)

requirements = checkbox(
    "Select your additive requirements:",
    choices=[
        "scheduling",
        questionary.Choice("sqlalchemy", checked=True),
        questionary.Choice("babel", checked=True),
        "security",
        questionary.Choice("events", checked=True),
        "cache",
        "mail",
        "jwt"
    ]
)

#------------------ app config -------------------#


def database_uri(name):
    return text(
        "DATABASE_URI: ",
        default=f"sqlite:///{name}.db"
    ).ask()


def additives(installed):
    choices = [
        fixed_choice(src[0], src)
        for src in installed
    ]
    return checkbox(
        "Enable your additives:     ",
        choices=choices
    ).ask()


redis_uri = text(
    "REDIS_URI:    ",
    default="redis://localhost:6379"
)

mail_username = text(
    "MAIL_USERNAME:",
    default=""
)

mail_password = text(
    "MAIL_PASSWORD:",
    default=""
)

extensions = checkbox(
    "Enable your app extensions:",
    choices=[
        "EXT_SCHEDULING",
        questionary.Choice("EXT_SQLALCHEMY", checked=True),
        questionary.Choice("EXT_BABEL", checked=True),
        "EXT_SECURITY",
        questionary.Choice("EXT_EVENTS", checked=True),
        "EXT_CACHE",
        "EXT_MAIL",
        "EXT_JWT"
    ]
)

features = checkbox(
    "Enable your app features:  ",
    choices=[
        questionary.Choice("WF_THEMES", checked=True),
        questionary.Choice("WF_TAILWIND", checked=True),
        "WF_CHECK_FRONTEND",
        "WF_BUILD_FRONTEND",
        questionary.Choice("WF_PROCESSING", checked=True),
        questionary.Choice("WF_ADDITIVES", checked=True)
    ]
)
