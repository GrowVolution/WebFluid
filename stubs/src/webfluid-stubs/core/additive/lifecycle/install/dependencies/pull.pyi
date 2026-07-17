from pathlib import Path

from webfluid.core.additive.main import Additive

def pull_dependency(
    additive: Additive, rid: str, constraint: str,
    additive_root: Path, seen: set[str]
) -> None: ...
