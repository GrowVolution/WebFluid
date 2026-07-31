from pathlib import Path
from importlib import import_module
import re, sys, shutil, json, typer

from . import templates
from webfluid.cli import questions
from webfluid.surface import dist
from webfluid.utils.additives import installed_additives


def make_defaults(base, api_init, api_v1, app_init, index_py):
    static_dir = base / "static"
    (static_dir / "img").mkdir(parents=True, exist_ok=True)
    (static_dir / "js").mkdir(exist_ok=True)

    (static_dir / "css").mkdir(exist_ok=True)
    (static_dir / "css/tailwind_raw.css").write_text(
        templates.tailwind_raw
    )

    (base / "templates").mkdir(exist_ok=True)

    (base / "api/v1").mkdir(parents=True, exist_ok=True)
    (base / "api/health.py").write_text(
        templates.health_py
    )
    (base / "api/v1/__init__.py").write_text(api_v1)
    (base / "api/__init__.py").write_text(api_init)

    (base / "app").mkdir(exist_ok=True)
    (base / "app/index.py").write_text(index_py)
    (base / "app/__init__.py").write_text(app_init)

    models = base / "models"
    models.mkdir(exist_ok=True)
    (models / "__init__.py").touch()

    schemas = base / "schemas"
    schemas.mkdir(exist_ok=True)
    (schemas / "__init__.py").touch()

    services = base / "services"
    services.mkdir(exist_ok=True)
    (services / "__init__.py").touch()

    events = base / "events"
    events.mkdir(exist_ok=True)
    (events / "__init__.py").touch()

    utils = base / "utils"
    utils.mkdir(exist_ok=True)
    (utils / "__init__.py").touch()


def frontend_conf():
    conf = {
        "type": questions.frontend_type.ask()
    }

    if conf["type"] == "htmx":
        conf["alpine"] = questions.use_alpine.ask()

    elif conf["type"] == "vite":
        conf["framework"] = questions.frontend_framework.ask()
        conf["typescript"] = questions.use_typescript.ask()
        conf["register_index"] = questions.register_index.ask()

    return conf


def inject_base(code, prefix=""):
    code = re.sub(
        r"defineConfig\(\s*{",
        (
            "defineConfig(({ command }) => ({\n"
            f"  base: command === 'build' ? '{prefix}/frontend/' : '/vite-dev/',"
        ),
        code,
        count=1
    )
    code = re.sub(r"\}\)\s*$", "}))", code)
    return code


def create_frontend(base, conf, space, name):
    if conf["type"] != "vite": return False

    template = conf["framework"]
    if template == "none": template = "vanilla"
    if conf["typescript"]: template += "-ts"

    template_src = dist / "vite-templates"
    template_dst = base / "frontend"
    shutil.copytree(
        template_src / template,
        template_dst
    )

    if template.endswith("ts"):
        config_file = template_dst / "vite.config.ts"
    else:
        config_file = template_dst / "vite.config.js"

    config = config_file.read_text() \
        if config_file.exists() \
        else templates.vite_base

    if space == "fluid":
        config_file.write_text(inject_base(config))
    else:
        config_file.write_text(
            inject_base(config, f"/{name}")
        )

    package_json = template_dst / "package.json"
    package = json.loads(package_json.read_text())
    package["name"] = f"@{space}/{name}-frontend"
    package["scripts"].pop("dev")
    if "&&" in package["scripts"]["build"]:
        tsc, build = package["scripts"]["build"].split(" && ")
        package["scripts"]["check"] = tsc
        package["scripts"]["build"] = build
    package_json.write_text(json.dumps(package, indent=2, ensure_ascii=False))

    return True


def setup_additives(config):
    additive_dir = Path("additives")
    if not additive_dir.exists() or not any(additive_dir.iterdir()):
        return

    if "additives" not in config:
        config["additives"] = {}

    additives = installed_additives(additive_dir)
    additives = [(a, p) for a, _, p in additives]
    selected_additives = questions.additives(additives)

    sys.path.append(str(additive_dir.parent))
    for selected in selected_additives:
        try:
            mod = import_module(f"additives.{selected[1]}")
            adtv = getattr(mod, "additive", None)
            if not adtv:
                raise ImportError("Failed to import 'additive: additive' from additive.")
            adtv.configure(config)
        except (ModuleNotFoundError, ImportError) as e:
            typer.echo(typer.style(f"[{selected[0]}] Failed to load additive: {e}",
                                   fg=typer.colors.YELLOW))

    for adtv in additives:
        config["additives"][adtv[0]] = "1" \
            if adtv in selected_additives \
            else "0"
