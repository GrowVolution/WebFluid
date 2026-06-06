from jinja2 import ChoiceLoader
from pathlib import Path
from importlib import import_module
from typing import TYPE_CHECKING
import json

from webfluid.core.additive import Additive, AdditiveVersion
from webfluid.core.constants import DEBUG, DEV_AUTO_INSTALL
from webfluid.utils.framework import enabled, try_import
from webfluid.utils.logging import factory as log_factory
from webfluid.exceptions import ManifestError

if TYPE_CHECKING:
    from webfluid.core.fluid import Fluid

_additives = {
    "additives": {},
    "bases": {}
}


def _load_additives(package: Path, target: str, additive_type: str, do_log: bool):
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


async def register_additives(fluid: "Fluid"):
    from webfluid.core.constants import ADDITIVES
    loaders = []

    async def register():
        nonlocal loaders

        for additive_info in installed_additives(fluid.additive_root, True):
            additive_id = additive_info[0]
            if not enabled(additive_id):
                continue

            try:
                mod = import_module(f"additives.{additive_info[2]}")
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
                loaders.append(additive.loader)
                log_factory.log(f"[{additive.name}] Additive successfully registered.")
            except Exception as e:
               log_factory.exception(e, f"[{additive.name}] Failed registering additive.")

    loaders.append(fluid.app_loader)
    if ADDITIVES: await register()
    loaders.append(fluid.framework_loader)

    fluid.jinja_env.loader = ChoiceLoader(loaders)


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


def import_base(base_id: str) -> Additive | None:
    entry_point = try_import("main")
    if not entry_point: return None

    for base in installed_bases(Path(
            entry_point.__file__
    ).parent / "additives"):
        if base[0] == base_id:
            pkg = base[2]
            break
    else: return None

    mod = import_module(f"additives.{pkg}")
    if not mod: return None

    additive = getattr(mod, "additive", None)
    if not additive or not additive.is_base:
        return None

    return additive
