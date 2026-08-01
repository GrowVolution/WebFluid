from pathlib import Path

from webfluid import Additive
from webfluid.utils.core import Version

_additives: dict[str, dict[Path, list[tuple[str, Version, str]]]]

def _load_additives(
    package: Path, target: str, additive_type: str, do_log: bool
) -> None: ...
def installed_additives(
    package: Path, do_log: bool = False, cache: bool = True
) -> list[tuple[str, Version, str]]: ...
def installed_bases(
    package: Path, do_log: bool = False, cache: bool = True
) -> list[tuple[str, Version, str]]: ...
def import_base(base_id: str) -> Additive | None: ...
