from jinja2 import ChoiceLoader
from pathlib import Path
from importlib import import_module
from typing import TYPE_CHECKING
import json

from webfluid.core.additive import Additive, AdditiveVersion
from webfluid.utils import enabled, try_import
from webfluid.utils.logging import factory as log_factory
from webfluid.exceptions import ManifestError

if TYPE_CHECKING:
    from webfluid import Fluid

_additives = {
    "additives": {},
    "bases": {}
}


def _load_additives(package: Path, target: str, additive_type: str, do_log: bool):
    from webfluid.core.manifest import Manifest

    for additive in package.iterdir():
        if not additive.is_dir(): continue

        try:
            manifest = Manifest(additive / "manifest.json")
            if manifest["type"] != additive_type: continue

            version = AdditiveVersion(*map(int, manifest["version"].split(".")))
            _additives[target][package].append(
                (manifest.get("id", additive.name), version, additive.name)
            )
        except (ModuleNotFoundError, FileNotFoundError, AttributeError, ManifestError, json.JSONDecodeError) as e:
            if do_log: log_factory.warning(f"Invalid additive package '{additive.name}' in {package}: {e}.")
            continue


async def register_additives(fluid: "Fluid"):
    from webfluid.core.constants import ADDITIVES
    loaders = []

    async def register():
        nonlocal loaders

        for additive_info in installed_additives(fluid.additive_root):
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
                if enabled("DEBUG_MODE"): additive.install()
                await additive.enable(fluid)
                loaders.append(additive.loader)
                log_factory.log(f"[{additive.additive_name}] Additive successfully registered.")
            except Exception as e:
               log_factory.exception(e, f"[{additive.additive_name}] Failed registering additive.")

    loaders.append(fluid.app_loader)
    if ADDITIVES: await register()
    loaders.append(fluid.framework_loader)

    fluid.jinja_env.loader = ChoiceLoader(loaders)


def installed_additives(package: Path, do_log: bool = False) -> list[tuple[str, str, str]]:
    if _additives["additives"].get(package):
        return _additives["additives"][package]

    if not package.name == "additives":
        raise ValueError(f"Invalid package name '{package.name}'.")

    _additives["additives"][package] = []
    _load_additives(
        package, "additives", "default", do_log
    )

    return _additives["additives"][package]


def installed_bases(package: Path, do_log: bool = False) -> list[tuple[str, str, str]]:
    if _additives["bases"].get(package):
        return _additives["bases"][package]

    _additives["bases"][package] = []
    _load_additives(
        package, "bases", "base", do_log
    )

    return _additives["bases"][package]


def import_base(additive_id: str) -> Additive | None:
    mod = try_import(f"additives.{additive_id}")
    if not mod: return None

    additive = getattr(mod, "additive", None)
    if not additive or not additive.is_base:
        return None

    return additive
