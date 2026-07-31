import questionary

frontend_type: questionary.Question
frontend_framework: questionary.Question
use_typescript: questionary.Question
register_index: questionary.Question
use_alpine: questionary.Question

def confirm_safe_id(given: str, suggestion: str) -> bool: ...
def select_base() -> str: ...
def additive_name(additive_id: str) -> str: ...

version_format: questionary.Question
as_base: questionary.Question
extend: questionary.Question
description: questionary.Question
author: questionary.Question
email: questionary.Question
requirements: questionary.Question

def database_uri(name: str) -> str: ...
def additives(installed: list[tuple[str, str]]) -> list[tuple[str, str]]: ...

redis_uri: questionary.Question
mail_username: questionary.Question
mail_password: questionary.Question
extensions: questionary.Question
features: questionary.Question
