from prompt_toolkit.formatted_text import HTML
from html import escape
from pathlib import Path
from typing import Any
import questionary

style = questionary.Style.from_dict({
    "qmark": "fg:#ff9d00 bold",
    "question": "bold",
    "pointer": "fg:#ff9d00 bold",
    "highlighted": "bold",
    "selected": "fg:#00aa00",
    "answer": "fg:#00aa00 bold",
    "separator": "fg:#888888",
    "text": "",

    "none": "fg:ansired",
    "htmx": "fg:ansiblue",
    "vite": "fg:ansimagenta",

    "react": "fg:ansicyan",
    "vue": "fg:ansigreen",
    "svelte": "fg:ansiyellow",
    "solid": "fg:ansiblue",
    "preact": "fg:ansiblue",
    "lit": "fg:ansiyellow",
    "qwik": "fg:ansiblue"
})

qmark = ">"
pointer = "•"


def choice(title: str, value: Any) -> questionary.Choice:
    return questionary.Choice(
        HTML(f"<{value}>{escape(title)}</{value}>").formatted_text,
        value=value
    )


def fixed_choice(title: str, value: Any) -> questionary.Choice:
    return questionary.Choice(
        HTML(f"<choice>{escape(title)}</choice>").formatted_text,
        value=value
    )


def select(message: str, choices: list[Any | questionary.Choice],
           **kwargs) -> questionary.Question:
    std = {
        "qmark": qmark,
        "pointer": pointer,
        "style": style
    }
    return questionary.select(
        message,
        choices=choices,
        **(std | kwargs)
    )


def checkbox(message: str, choices: list[Any | questionary.Choice],
             **kwargs) -> questionary.Question:
    std = {
        "qmark": qmark,
        "pointer": pointer
    }
    return questionary.checkbox(
        message,
        choices=choices,
        **(std | kwargs)
    )


def text(message: str, **kwargs) -> questionary.Question:
    std = {
        "qmark": qmark,
        "style": style
    }
    return questionary.text(
        message,
        **(std | kwargs)
    )


def confirm(message: str, **kwargs) -> questionary.Question:
    std = {
        "qmark": qmark,
        "style": style
    }
    return questionary.confirm(
        message,
        **(std | kwargs)
    )


###################################################
#                   wf create                     #
###################################################

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


def confirm_safe_id(given: str, suggestion: str) -> bool:
    return confirm(
        f"Invalid id format '{given}'. Continue with '{suggestion}' instead?",
        default=True
    ).ask()


def select_base() -> str:
    from webfluid.additives.core import installed_bases
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


def additive_name(additive_id: str) -> str:
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


def database_uri(name: str) -> str:
    return text(
        "DATABASE_URI: ",
        default=f"sqlite:///{name}.db"
    ).ask()


def additives(installed: list[tuple[str, str]]) -> list[str]:
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
        questionary.Choice("WF_PROCESSING", checked=True),
        questionary.Choice("WF_ADDITIVES", checked=True)
    ]
)

###################################################
#                    wf run                       #
###################################################

host = text(
    "Enter the host address:",
    default="127.0.0.1"
)

port = text(
    "Enter the port number: ",
    default="8000",
    validate=lambda x: x.isdigit()
)

debug_mode = confirm(
    "Run in debug mode?     ",
    default=False
)

menu = select(
    "What do you want to do:",
    choices=[
        fixed_choice("🔄  Restart", 0),
        fixed_choice("⏹  Stop", 1),
        fixed_choice("▶  Start (if stopped)", 2),

        fixed_choice("📜  Join log (console)", 3),
        fixed_choice("🗑  Clear log folder", 4),

        fixed_choice("🧹  Clear console", 5),

        fixed_choice("🚪  Exit", 6)
    ]
)
