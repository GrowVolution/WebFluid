from pathlib import Path
from functools import wraps
from importlib import import_module
import json

from webfluid.core.constants import DEBUG, DEV_AUTO_INSTALL
from webfluid.exceptions import ManifestError

_additives = {
    "additives": {},
    "bases": {}
}


def _load_additives(package, target, additive_type, do_log):
    from webfluid.core.additive import AdditiveVersion, Manifest

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
            if do_log:
                from .logging import factory as log_factory
                log_factory.warning(f"Invalid additive package '{additive.name}' in {package}:\n{e}")
            continue


def installed_additives(package, do_log=False, cache=True):
    if  _additives["additives"].get(package):
        return _additives["additives"][package]

    if not package.name == "additives":
        raise ValueError(f"Invalid package name '{package.name}'.")

    _additives["additives"][package] = []
    _load_additives(
        package, "additives", "default", do_log
    )

    return _additives["additives"][package] if cache else _additives["additives"].pop(package)


def installed_bases(package, do_log=False, cache=True):
    if _additives["bases"].get(package):
        return _additives["bases"][package]

    _additives["bases"][package] = []
    _load_additives(
        package, "bases", "base", do_log
    )

    return _additives["bases"][package] if cache else _additives["bases"].pop(package)


def import_base(base_id):
    from .core import try_import
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


def id_check(additive_id):
    from .core import safe_string
    safe_id = safe_string(additive_id)
    if additive_id != safe_id:
        return False, f"Invalid id format '{additive_id}'. Try '{safe_id}' for example."
    return True, additive_id


def version_check(v):
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
            from .core import final_version
            v, _, b = final_version(v_number)
            if v < 0 or v > 999:
                return False, "Version number cannot be negative or greater than 999."
            if b < 1 or b > 9:
                return False, "Build number cannot smaller than 1 or greater than 9."

    return True, version_str


def type_check(t):
    if t not in ("base", "default"):
        return False, f"Invalid type string '{t}'."
    return True, t


def require_extensions(*extensions):
    def decorator(fn):
        from .core import enabled, async_result
        from .logging import factory as log_factory

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


async def register_additives(fluid):
    from webfluid.core.additive import Additive
    from .core import enabled
    from .logging import factory as log_factory

    for additive_info in installed_additives(fluid.additive_root, True):
        additive_id = additive_info[0]
        if not enabled(additive_id):
            continue

        try: mod = import_module(f"additives.{additive_info[2]}")
        except ModuleNotFoundError as e:
            log_factory.exception(e, f"Could not import additive '{additive_id}' for app '{fluid.name}'.")
            continue

        additive = getattr(mod, "additive", None)
        if not isinstance(additive, Additive):
            log_factory.error(f"Missing 'additive: Additive' in additive package of '{additive_id}'.")
            continue

        try:
            log_factory.log(f"Registering: {additive}")
            if DEBUG and DEV_AUTO_INSTALL: additive.install()
            await additive.enable(fluid)
            log_factory.log(f"[{additive.name}] Additive successfully registered.")
        except Exception as e:
            log_factory.exception(e, f"[{additive.name}] Failed registering additive.")
