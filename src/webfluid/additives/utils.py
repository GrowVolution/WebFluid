from pathlib import Path
from functools import wraps
from typing import TYPE_CHECKING, Optional
import json

from webfluid.utils.logging import factory as log_factory
from webfluid.exceptions import ManifestError
from webfluid.utils.framework import (
    try_import, safe_string, final_version, enabled, async_result
)

if TYPE_CHECKING:
    from webfluid import Additive

_additives = {
    "additives": {},
    "bases": {}
}


def _load_additives(package: Path, target: str, additive_type: str, do_log: bool):
    from webfluid.core.additive import AdditiveVersion
    from webfluid.core.manifest import Manifest

    for additive in package.iterdir():
        if not additive.is_dir(): continue
        elif additive.name == "__pycache__": continue

        try:
            manifest = Manifest(additive / "manifest.json")
            if manifest["type"] != additive_type: continue
            version = AdditiveVersion(*manifest["version"].split("."))
            _additives[target][package].append(
                (manifest.get("id", additive.name), version, additive.name)
            )
        except (ModuleNotFoundError, FileNotFoundError, AttributeError, ManifestError, json.JSONDecodeError) as e:
            if do_log: log_factory.warning(f"Invalid additive package '{additive.name}' in {package}:\n{e}")
            continue


def installed_additives(package: Path, do_log: bool = False, cache: bool = True) -> list[tuple[str, str, str]]:
    if  _additives["additives"].get(package):
        return _additives["additives"][package]

    if not package.name == "additives":
        raise ValueError(f"Invalid package name '{package.name}'.")

    _additives["additives"][package] = []
    _load_additives(
        package, "additives", "default", do_log
    )

    return _additives["additives"][package] if cache else _additives["additives"].pop(package)


def installed_bases(package: Path, do_log: bool = False, cache: bool = True) -> list[tuple[str, str, str]]:
    if _additives["bases"].get(package):
        return _additives["bases"][package]

    _additives["bases"][package] = []
    _load_additives(
        package, "bases", "base", do_log
    )

    return _additives["bases"][package] if cache else _additives["bases"].pop(package)


def import_base(base_id: str) -> Optional[Additive]:
    entry_point = try_import("main")
    if not entry_point: return None

    for base in installed_bases(Path(
            entry_point.__file__
    ).parent / "additives"):
        if base[0] == base_id:
            pkg = base[2]
            break
    else: return None

    mod = try_import(f"additives.{pkg}")
    if not mod: return None

    additive = getattr(mod, "additive", None)
    if not additive or not additive.is_base:
        return None

    return additive


def id_check(additive_id: str) -> tuple[bool, str]:
    safe_id = safe_string(additive_id)
    if additive_id != safe_id:
        return False, f"Invalid id format '{additive_id}'. Try '{safe_id}' for example."
    return True, additive_id


def version_check(v: str) -> tuple[bool, str]:
    version_str = v.lower().strip()
    if not version_str:
        return False, "Additive version not defined."

    first_char_invalid = not version_str[0].isdigit()

    if  first_char_invalid:
        return False, "Invalid version string format."

    v_numbers = version_str.split(" ")[0].split(".")
    if len(v_numbers) > 3:
        return False, "Too many version numbers."

    for v_number in v_numbers:
        if not v_number.isdigit() and \
                v_numbers.index(v_number) != len(v_numbers) - 1:
            return False, "Invalid version number format."
        elif not v_number.isdigit():
            if not (
                    "a" in v_number and len(v_number.split("a")) == 2 or
                    "b" in v_number and len(v_number.split("b")) == 2 or
                    "rc" in v_number and len(v_number.split("rc")) == 2
            ): return False, "Invalid version number format."

        if v_number.isdigit():
            v = int(v_number)
            if v < 0 or v > 999:
                return False, "Version number cannot be negative or greater than 999."

        else:
            v, _, b = final_version(v_number)
            if v < 0 or v > 999:
                return False, "Version number cannot be negative or greater than 999."
            if b < 1 or b > 9:
                return False, "Build number cannot smaller than 1 or greater than 9."

    return True, version_str


def type_check(t: str) -> tuple[bool, str]:
    if t not in ("base", "default"):
        return False, f"Invalid type string '{t}'."
    return True, t


def require_extensions(*extensions):
    def decorator(fn):
        from webfluid.utils.logging import factory as log_factory

        @wraps(fn)
        async def wrapper(*args, **kwargs):
            for ext in extensions:
                if not isinstance(ext, str):
                    log_factory.warning(f"Invalid extension '{ext}'.")
                    continue

                if not enabled(f"EXT_{ext.upper()}"):
                    raise RuntimeError(f"Extension '{ext}' is not enabled.")
            return await async_result(fn(*args, **kwargs))

        return wrapper
    return decorator
