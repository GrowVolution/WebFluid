from pathlib import Path
from configparser import ConfigParser
from secrets import token_hex
from importlib import import_module
import typer, json, shutil, re, sys

from webfluid.cli import questions
from webfluid.cli.create import templates
from webfluid.core.constants import FRAMEWORK_ID
from webfluid.surface import node_cmd, dist
from webfluid.utils.additives import installed_additives
from webfluid.utils.core import safe_string

create = typer.Typer(help="Create new WebFluid instances.")

def _make_defaults(base, api_init, api_v1, app_init, index_py):
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


def _frontend_conf():
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


def _inject_base(code, prefix=""):
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


def _create_frontend(base, conf, space, name):
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
        config_file.write_text(_inject_base(config))
    else:
        config_file.write_text(
            _inject_base(config, f"/{name}")
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


def _setup_additives(config):
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


@create.command()
def project(
        name: str,
        skip_defaults: bool = typer.Option(
            False,
            "--skip-defaults", "-sd",
            help="Skip creating the default structure."
        ),
        skip_frontend: bool = typer.Option(
            False,
            "--skip-frontend", "-sf",
            help="Skip setting up the frontend tooling."
        ),
        babel_fallback: bool = typer.Option(
            False,
            "--babel-fallback", "-bf",
            help="Extract Babel translation catalogs "
                 "for fallback translations."
        )
):
    project_root = Path(name).resolve()
    if project_root.exists() and any(project_root.iterdir()):
        typer.secho(
            f"Directory '{name}' already exists and is not empty.",
            fg=typer.colors.RED
        )
        raise typer.Exit(1)

    typer.echo(f"Creating project '{name}'...")
    project_root.mkdir(parents=True, exist_ok=True)

    app_dir = project_root / "fluid"

    if not skip_defaults:
        typer.secho("Generating default structure...",
                    bold=True)

        _make_defaults(
            app_dir,
            templates.api_router_py,
            templates.app_v1_py,
            templates.app_router_py,
            templates.app_index_py
        )

        (project_root / "additives").mkdir(exist_ok=True)
        (project_root / ".gitignore").write_text(
            templates.app_gitignore
        )

    def frontend():
        typer.secho("Setting up frontend...", bold=True)

        from webfluid.surface import setup_frontend
        setup_frontend(name)

        if skip_defaults: return

        conf = _frontend_conf()
        if _create_frontend(app_dir, conf, "fluid", name):
            node_cmd(
                ["npm", "install"],
                project_root
            )
            node_cmd(
                ["npm", "install", "-w", "fluid/frontend"],
                project_root
            )

            shutil.rmtree(app_dir / "app", ignore_errors=True)
            (project_root / "main.py").write_text(
                templates.main_py.format(index="")
            )
        else:
            node_cmd(
                ["npm", "install"],
                project_root
            )

            (app_dir / "templates/index.html").write_text(
                templates.app_index_html
            )
            (project_root / "main.py").write_text(
                templates.main_py.format(
                    index="""
    from fluid.app import app_router
    app.include_router(app_router)
                """)
            )

        conf_list = str(conf).strip("{}").split(", ")
        conf_str = ("{\n\t\t"
                   f"{',\n\t\t'.join(conf_list)}"
                    "\n\t}")
        (app_dir / "config.py").write_text(
            templates.app_config_py.format(
                name=name,
                frontend=conf_str
            )
        )

    if not skip_frontend: frontend()

    if babel_fallback:
        typer.secho("Extracting Babel fallback catalogs...",
                    bold=True)

        from webfluid.extensions.babel import Babel
        Babel.extract_fallback(project_root)

    typer.secho(f"Successfully created project '{name}'.",
                bold=True, fg=typer.colors.GREEN)


@create.command()
def additive(additive_id: str):
    if additive_id == FRAMEWORK_ID:
        typer.secho(
            "Additive ID cannot be the same as the framework ID.",
            fg=typer.colors.RED
        )
        raise typer.Exit(1)

    safe_id = safe_string(additive_id)
    if additive_id != safe_id:
        if not questions.confirm_safe_id(additive_id, safe_id):
            typer.secho("Aborting...", fg=typer.colors.YELLOW)
            raise typer.Exit()

    additive_root = Path(f"additives/{safe_id}").resolve()
    if additive_root.exists() and any(additive_root.iterdir()):
        typer.secho(
            f"Directory '{safe_id}' already exists and is not empty.",
            fg=typer.colors.RED
        )
        raise typer.Exit(1)

    from webfluid import version

    manifest = {
        "id": safe_id,
        "version": questions.version_format.ask(),
        "name": questions.additive_name(safe_id),
        "description": questions.description.ask(),
        "authors": [],
        "requires": {
            "wf": f">={str(version()).lstrip('v')}",
            "additives": {},
            "packages": []
        }
    }

    author = {}
    name = questions.author.ask()
    if name: author["name"] = name
    email = questions.email.ask()
    if email: author["email"] = email
    if author: manifest["authors"].append(author)

    as_base = questions.as_base.ask()
    import_base_fn = ""
    base_import = ""

    if as_base:
        manifest["type"] = "base"
        manifest["frontend"] = { "type": "none" }
        index_html = templates.adtv_index_html.format(
            name=manifest["name"]
        )
    else:
        manifest["type"] = "default"

        extend = questions.extend.ask()
        if extend:
            selected_base = questions.select_base()
            import_base_fn = "from webfluid.utils.additives import import_base\n"
            base_import = f'\n\timport_base("{selected_base}"),'
            manifest["requires"]["additives"][selected_base] = "*"

        manifest["frontend"] = _frontend_conf()
        if _create_frontend(
                additive_root,
                manifest["frontend"],
                "additive",
                safe_id.replace("_", "-")
        ):
            index_html = None
            node_cmd(
                ["npm", "install", "-w", f"additives/{safe_id}/frontend"],
                Path.cwd()
            )
        else:
            index_html = templates.adtv_index_html.format(
                name=manifest["name"]
            )

    requirements = questions.requirements.ask()
    if requirements:
        copy = requirements.copy()
        requirements = [f"\t\t\"{r}\"," for r in copy]
        requirements_str = f"[\n{'\n'.join(requirements)}\n\t]"
        if not base_import:
            requirements_str = "\n\trequired_extensions=" + requirements_str
        else:
            requirements_str = "\n\t" + requirements_str
        requirements = requirements_str
    else:
        requirements = ""

    typer.secho(f"Creating additive '{safe_id}'...", bold=True)

    _make_defaults(
        additive_root,
        templates.api_py,
        templates.adtv_v1_py,
        templates.app_py,
        templates.adtv_index_py
    )

    if index_html:
        (additive_root / "templates/index.html").write_text(
            index_html, encoding="utf-8"
        )
        index_registry = """
    from .app import index
    additive.app.get("/")(index)
        """
    else:
        shutil.rmtree(additive_root / "app", ignore_errors=True)
        index_registry = ""

    (additive_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False)
    )
    (additive_root / "__init__.py").write_text(
        templates.init_py.format(
            import_base=import_base_fn,
            base=base_import,
            requirements=requirements,
            index=index_registry
        )
    )
    (additive_root / ".gitignore").write_text(
        templates.adtv_gitignore
    )


@create.command("app")
def create_app(
        name: str,
        secret_length: int = typer.Option(
            32,
            "--secret-length", "-sl",
            help="Length of the secret key."
        )
):
    config_root = Path("app_configs").resolve()
    config_root.mkdir(exist_ok=True)

    config_file = config_root / f"{name}.ini"
    if config_file.exists():
        typer.secho(
            f"Config file '{name}.ini' already exists.",
            fg=typer.colors.RED
        )
        raise typer.Exit(1)

    config = ConfigParser()
    config.optionxform = str

    config["general"] = {
        "SECRET_KEY": token_hex(secret_length)
    }

    config["extensions"] = {}
    extensions = (
        "EXT_SCHEDULING",
        "EXT_SQLALCHEMY",
        "EXT_BABEL",
        "EXT_SECURITY",
        "EXT_EVENTS",
        "EXT_CACHE",
        "EXT_MAIL",
        "EXT_JWT"
    )
    enable_extensions = questions.extensions.ask()
    for ext in extensions:
        enabled = ext in enable_extensions
        config["extensions"][ext] = "1" if enabled else "0"

    config["features"] = {}
    features = (
        "WF_THEMES",
        "WF_TAILWIND",
        "WF_PROCESSING",
        "WF_ADDITIVES"
    )
    enable_features = questions.features.ask()
    for feat in features:
        enabled = feat in enable_features
        config["features"][feat] = "1" if enabled else "0"

    _setup_additives(config)

    if "EXT_SECURITY" in enable_extensions:
        config["security"] = {
            "SECURITY_SECRET": token_hex(32)
        }

    print()
    config["data"] = {
        "DATABASE_URI": questions.database_uri(name),
        "REDIS_URI": questions.redis_uri.ask()
    }

    if "EXT_MAIL" in enable_extensions:
        print()
        config["mail"] = {
            "MAIL_USERNAME": questions.mail_username.ask(),
            "MAIL_PASSWORD": questions.mail_password.ask()
        }

    with open(config_file, "w") as f: config.write(f)


def cli_entry(app):
    app.add_typer(create, name="create")
