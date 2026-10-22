import re
from pathlib import Path

OPEN: str
CLOSE: str
LINKED: re.Pattern[str]
LEAD: str
SKILL_LEAD: str
LINKED_LEAD: str
SKIPPED: frozenset[str]

__all__ = ["OPEN", "CLOSE", "LEAD", "SKILL_LEAD", "discover", "index"]

def index(
    path: str | Path, lead: str | None = None, write: bool = True, seen: frozenset[Path] = ...
) -> bool: ...
def discover(root: str | Path) -> list[Path]: ...
