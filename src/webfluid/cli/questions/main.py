from prompt_toolkit.formatted_text import HTML
from html import escape
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


def choice(title, value):
    return questionary.Choice(
        HTML(f"<{value}>{escape(title)}</{value}>").formatted_text,
        value=value
    )


def fixed_choice(title, value):
    return questionary.Choice(
        HTML(f"<choice>{escape(title)}</choice>").formatted_text,
        value=value
    )


def select(message, choices, **kwargs):
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


def checkbox(message, choices, **kwargs):
    std = {
        "qmark": qmark,
        "pointer": pointer
    }
    return questionary.checkbox(
        message,
        choices=choices,
        **(std | kwargs)
    )


def text(message, **kwargs):
    std = {
        "qmark": qmark,
        "style": style
    }
    return questionary.text(
        message,
        **(std | kwargs)
    )


def confirm(message, **kwargs):
    std = {
        "qmark": qmark,
        "style": style
    }
    return questionary.confirm(
        message,
        **(std | kwargs)
    )


def password(message, **kwargs):
    std = {
        "qmark": qmark,
        "style": style
    }
    return questionary.password(
        message,
        **(std | kwargs)
    )
