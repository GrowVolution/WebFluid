from pathlib import Path
from typing import Any

_static_js: Path

def setup_frontend(project: str) -> None: ...
def validate_config(f: dict[str, Any]) -> tuple[bool, str | dict[str, Any]]: ...
