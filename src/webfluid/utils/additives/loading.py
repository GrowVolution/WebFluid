from pathlib import Path
import json

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
                from ..logging import factory as log_factory
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
    from ..core import try_import
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
