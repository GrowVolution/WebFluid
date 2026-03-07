from jinja2 import ChoiceLoader
from pathlib import Path
from importlib import import_module
from configparser import ConfigParser
from typing import TYPE_CHECKING
import typer, json

from webfluid.core.manifest import Manifest
from webfluid.core.additive import Additive, AdditiveVersion
from webfluid.utils import enabled
from webfluid.utils.logging import factory as log_factory
from webfluid.exceptions import ManifestError

if TYPE_CHECKING:
    from webfluid import Fluid

additives_home = Path.cwd() / "additives"
conf_path = Path.cwd() / "app_configs"
_additives = {}


def setup_additives(app_name: str):
    conf = conf_path / f"{app_name}.conf"
    config = ConfigParser()
    config.optionxform = str

    conf_exists = conf.exists()
    if conf_exists:
        config.read(conf)
    if "additives" not in config:
        config["additives"] = {}

    typer.echo("\n" +
               typer.style("Okay, now you can activate your installed additives.\n", fg=typer.colors.YELLOW, bold=True) +
               typer.style("Default is '0' (deactivated)!", fg=typer.colors.MAGENTA))

    for additive_info in installed_additives(additives_home):
        adtv_id = additive_info[0]
        val = input(f"<{adtv_id} {additive_info[1]}>: ").strip()
        if not val:
            val = "0"
        config["additives"][adtv_id] = val

        if val.lower() in ("1", "y", "yes"):
            try:
                mod = import_module(f"additives.{additive_info[2]}")
                additive = getattr(mod, "additive", None)
                if not additive:
                    raise ImportError("Failed to import 'additive: additive' from additive.")
                additive.setup_config(config, conf_exists)
            except (ModuleNotFoundError, ImportError) as e:
                typer.echo(typer.style(f"[{adtv_id}] Failed to load additive: {e}", fg=typer.colors.YELLOW))

    with open(conf, "w") as f:
        config.write(f)


def register_additives(fluid: "Fluid"):
    loaders = []

    def register():
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
                additive.enable(fluid)
                loaders.append(additive.loader)
                log_factory.log(f"[{additive.additive_name}] Additive successfully registered.")
            except Exception as e:
               log_factory.exception(e, f"[{additive.additive_name}] Failed registering additive.")

    loaders.append(fluid.app_loader)
    if enabled("WF_ADDITIVES"): register()
    loaders.append(fluid.framework_loader)

    fluid.jinja_env.loader = ChoiceLoader(loaders)


def installed_additives(package: Path, do_log: bool = False) -> list[tuple[str, str, str]]:
    if _additives.get(package):
        return _additives[package]

    if not package.name == "additives":
        raise ValueError(f"Invalid package name '{package.name}'.")

    _additives[package] = []

    for additive in package.iterdir():
        if not additive.is_dir():
            continue

        try:
            manifest = Manifest(additive / "manifest.json")
            version = AdditiveVersion(*map(int, manifest["version"].split(".")))

            if "type" in manifest and manifest["type"] == "base":
                continue

            _additives[package].append(
                (manifest.get("id", additive.name), version, additive.name)
            )
        except (ModuleNotFoundError, FileNotFoundError, AttributeError, ManifestError, json.JSONDecodeError) as e:
            if do_log: log_factory.warn(f"Invalid module package '{additive.name}' in {package}: {e}.")
            continue

    return _additives[package]


def import_base(module_id: str) -> Additive | None:
    try:
        mod = import_module(f"additives.{module_id}")
        additive = getattr(mod, "additive", None)
        if not additive or not additive.is_base:
            return None
        return additive
    except ModuleNotFoundError:
        return None
