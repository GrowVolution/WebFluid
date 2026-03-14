from prompt_toolkit.formatted_text import HTML
from pathlib import Path
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


def choice(title: str, value: str) -> questionary.Choice:
    return questionary.Choice(
        HTML(f"<{value}>{title}</{value}>").formatted_text,
        value=value
    )


###################################################
#                   wf create                     #
###################################################

frontend_type = questionary.select(
    "Select your frontend type:",
    choices=[
        choice("🚫 None", "none"),
        choice("</> HTMX", "htmx"),
        choice("⚡ Vite", "vite"),
    ],
    default="none",
    qmark=qmark,
    pointer=pointer,
    style=style
)

frontend_framework = questionary.select(
    "Select your frontend framework:",
    choices=[
        choice("🚫 None", "none"),
        choice("⚛ React", "react"),
        choice("🟢 Vue", "vue"),
        choice("🔥 Svelte", "svelte"),
        choice("◆ Solid", "solid"),
        choice("📦 Preact", "preact"),
        choice("💡 Lit", "lit"),
        choice("⚡ Qwik", "qwik"),
    ],
    default="none",
    qmark=qmark,
    pointer=pointer,
    style=style
)

use_typescript = questionary.confirm(
    "Do you want to use TypeScript?",
    default=False,
    qmark=qmark,
    style=style
)

use_alpine = questionary.confirm(
    "Do you want to use AlpineJS?",
    default=False,
    qmark=qmark,
    style=style
)

#-------------- additive manifest-----------------#


def confirm_safe_id(given: str, suggestion: str) -> bool:
    return questionary.confirm(
        f"Invalid id format '{given}'. Continue with '{suggestion}' instead?",
        default=True,
        qmark=qmark,
        style=style
    ).ask()


def select_base() -> str:
    from webfluid.additives import installed_bases
    bases = installed_bases(Path.cwd() / "additives")
    if len(bases) == 0:
        raise ValueError("There are no base additives installed.")

    choices = [
        choice(f"<{base_id} {version}>", base_id)
        for base_id, version, _ in bases
    ]
    return questionary.select(
        "Select your base additive:",
        choices=choices,
        default=choices[0],
        qmark=qmark,
        pointer=pointer,
        style=style
    ).ask()


def additive_name(additive_id: str) -> str:
    parts = additive_id.split("_")
    for i, part in enumerate(parts):
        parts[i] = part.capitalize()
    default = " ".join(parts)
    return questionary.text(
        f"Enter your additive name ({default}):",
        default=default,
        qmark=qmark,
        style=style
    ).ask()


version_format = questionary.select(
    "Select a version format:",
    choices=[
        "1",
        "1.0",
        "1.0.0"
    ],
    default="1.0",
    qmark=qmark,
    pointer=pointer,
    style=style
)

as_base = questionary.confirm(
    "Do you want to create a base additive?",
    default=False,
    qmark=qmark,
    style=style
)

description = questionary.text(
    "Describe your additive:",
    default="",
    qmark=qmark,
    style=style
)

author = questionary.text(
    "Enter your name or nickname:",
    default="",
    qmark=qmark,
    style=style
)

email = questionary.text(
    "Enter your email address:",
    default="",
    qmark=qmark,
    style=style
)

requirements = questionary.checkbox(
    "Select your additive requirements:",
    choices=[
        "scheduling",
        questionary.Choice("sqlalchemy", checked=True),
        questionary.Choice("babel", checked=True),
        "oauth",
        "cache",
        "mail",
        "jwt"
    ],
    qmark=qmark,
    style=style
)
