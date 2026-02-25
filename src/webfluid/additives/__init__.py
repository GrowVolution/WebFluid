from jinja2 import ChoiceLoader, PrefixLoader, FileSystemLoader
from pathlib import Path
from importlib import import_module
from configparser import ConfigParser
from typing import TYPE_CHECKING
import os, typer, json

from webfluid.utils.additive import basic_checked_data, valid_version
from flaskpp.utils import enabled
from flaskpp.utils.logging import log, error, warn, exception
from flaskpp.exceptions import ManifestError

if TYPE_CHECKING:
    from flask import Flask
    from flaskpp import FlaskPP, additive

additives_home = None
conf_path = None
_additives = {}


def setup_globals() -> tuple[Path, Path]:
    global additives_home, conf_path

    from flaskpp.cli import cwd
    additives_home = cwd / "additives"
    conf_path = cwd / "app_configs"

    return additives_home, conf_path


def generate_modlib(app_name: str):
    setup_globals()

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

    for additives_info in installed_additives(additives_home, False):
        mod_id = additives_info[0]
        val = input(f"<{mod_id} {additives_info[1]}>: ").strip()
        if not val:
            val = "0"
        config["additives"][mod_id] = val

        if val.lower() in ("1", "y", "yes"):
            try:
                mod = import_module(f"additives.{additive_info[2]}")
                additive = getattr(mod, "additive", None)
                if not additive:
                    raise ImportError("Failed to import 'additive: additive' from additive.")
                additive.setup_config(config, conf_exists)
            except (ModuleNotFoundError, ImportError) as e:
                typer.echo(typer.style(f"[{mod_id}] Failed to load additive: {e}", fg=typer.colors.YELLOW))

    set_home = input(
        "\n" +
        typer.style("Do you want to define a home additive?", fg=typer.colors.YELLOW, bold=True) +
        " (Y/n): "
    ).lower().strip()

    if set_home not in {"n", "no", "0"}:
        typer.echo(typer.style(
            "Okay choose your home additive:",
            fg=typer.colors.MAGENTA,
            bold=True
        ))

        choices = list(config["additives"].keys())
        for idx, additive in enumerate(choices, start=1):
            typer.echo("\t" + typer.style(f"{idx}. {additive}", bold=True))

        while True:
            choice = input("> ").strip()
            try:
                choice = int(choice) - 1
                home_additive = choices[choice]
                break
            except (ValueError, IndexError):
                typer.echo(typer.style(
                    "Invalid input. Try again:",
                    fg=typer.colors.RED,
                    bold=True
                ))

        config["additives"]["HOME_MODULE"] = home_additive

    with open(conf, "w") as f:
        config.write(f)


def register_additives(app: "FlaskPP | Flask"):
    app_name = os.getenv("APP_NAME")
    if not app_name:
        raise RuntimeError("Missing app name variable: APP_NAME")

    loader_context = {}
    primary_loader = None

    def register():
        nonlocal loader_context, primary_loader

        for additive_info in installed_additives(Path(app.root_path) / "additives", False):
            mod_id = additive_info[0]
            if not enabled(mod_id):
                continue

            try:
                mod = import_module(f"additives.{additive_info[2]}")
            except ModuleNotFoundError as e:
                exception(e, f"Could not import additive '{mod_id}' for app '{app_name}'.")
                continue

            from flaskpp import Module
            additive = getattr(mod, "additive", None)
            if not isinstance(additive, Module):
                error(f"Missing 'additive: Module' in additive '{mod_id}'.")
                continue

            try:
                log(f"Registering: {additive}")
            except ManifestError as e:
                exception(e)
                continue

            try:
                if enabled("DEBUG_MODE"):
                    additive.extract()
                    additive.install_packages()

                is_home = os.getenv("HOME_MODULE", "").lower() == mod_id
                additive.enable(app, is_home)

                loader_path = additive.import_name.replace('.', '/')
                if additive.base:
                    additive_loader = ChoiceLoader([
                        FileSystemLoader(f"{loader_path}/templates"),
                        FileSystemLoader(f"{additive.base.import_name.replace('.', '/')}/templates")
                    ])
                else:
                    additive_loader = FileSystemLoader(f"{loader_path}/templates")

                loader_context[additive.name] = additive_loader
                if is_home:
                    primary_loader = loader_context[additive.name]

                log(f"[{additive.additive_name}] Registered additive as {'home' if is_home else 'path'}.")

            except Exception as e:
                exception(e, f"[{additive.additive_name}] Failed registering additive.")

    if enabled("FPP_additives"): register()

    loaders = []
    app_loader = FileSystemLoader("templates")
    fpp_loader = FileSystemLoader(str((Path(__file__).parent.parent / "app" / "templates").resolve()))

    if primary_loader:
        loaders.append(primary_loader)

    loaders.append(ChoiceLoader([
        app_loader, PrefixLoader({ "app": app_loader })
    ]))

    loaders.append(PrefixLoader(loader_context))

    loaders.append(ChoiceLoader([
        fpp_loader, PrefixLoader({ "flaskpp": fpp_loader })
    ]))

    app.jinja_loader = ChoiceLoader(loaders)
    log(f"[{__name__}] additives registered.")


def installed_additives(package: Path, do_log: bool = True) -> list[tuple[str, str, str]]:
    if _additives.get(package):
        return _additives[package]

    if not package.name == "additives":
        raise ValueError(f"Invalid package name '{package.name}'.")

    _additives[package] = []

    for additive in package.iterdir():
        if not additive.is_dir():
            continue

        try:
            manifest = additive / "manifest.json"
            additive_data = basic_checked_data(manifest)
            version = valid_version(additive_data["version"])

            if "type" in module_data and module_data["type"] == "base":
                continue

            _additives[package].append(
                (module_data.get("id", module.name), version, module.name)
            )
        except (ModuleNotFoundError, FileNotFoundError, AttributeError, ManifestError, json.JSONDecodeError) as e:
            if do_log: warn(f"Invalid module package '{module.name}' in {package}: {e}.")
            continue

    return _additives[package]


def import_base(module_id: str) -> "Module | None":
    try:
        mod = import_module(f"additives.{module_id}")
        module = getattr(mod, "module", None)
        if not module or not module.is_base:
            return None
        return module
    except ModuleNotFoundError:
        return None
