from pathlib import Path
import typer, json, shutil

from webfluid.cli import templates, questions
from webfluid.surface import node_cmd, dist
from webfluid.utils import safe_string

create = typer.Typer(help="Create a new WebFluid instances.")


def _make_defaults(
        base: Path,
        api_init: str,
        app_init: str,
        index_py: str,
        index_html: str,
):
    static_dir = base / "static"
    (static_dir / "img").mkdir(parents=True, exist_ok=True)
    (static_dir / "js").mkdir(exist_ok=True)

    (static_dir / "css").mkdir(exist_ok=True)
    (static_dir / "css/tailwind_raw.css").write_text(
        templates.tailwind_raw
    )

    (base / "templates").mkdir(exist_ok=True)
    (base / "templates/index.html").write_text(
        index_html
    )

    (base / "api/v1").mkdir(parents=True, exist_ok=True)
    (base / "api/v1/health.py").write_text(
        templates.health_py
    )
    (base / "api/v1/__init__.py").write_text(
        templates.v1_py
    )
    (base / "api/__init__.py").write_text(api_init)

    (base / "app").mkdir(exist_ok=True)
    (base / "app/index.py").write_text(index_py)
    (base / "app/__init__.py").write_text(app_init)

    (base / "models").mkdir(exist_ok=True)
    (base / "schemas").mkdir(exist_ok=True)
    (base / "services").mkdir(exist_ok=True)


def _frontend_conf() -> dict:
    conf = {
        "type": questions.frontend_type.ask()
    }

    if conf["type"] == "htmx":
        conf["alpine"] = questions.use_alpine.ask()

    elif conf["type"] == "vite":
        conf["framework"] = questions.frontend_framework.ask()
        conf["typescript"] = questions.use_typescript.ask()

    return conf


def _create_frontend(base: Path, conf: dict, space: str, name: str) -> bool:
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

    node_cmd(
        ["npm", "pkg", "set", f"name='@{space}/{name}-frontend'"],
        template_dst
    )
    node_cmd(
        ["npm", "pkg", "delete", "scripts.dev"],
        template_dst
    )

    return True


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
            templates.app_router_py,
            templates.app_index_py,
            templates.app_index_html
        )

        (project_root / "main.py").write_text(
            templates.main_py
        )
        (project_root / ".gitignore").write_text(
            templates.gitignore
        )

    def frontend():
        typer.secho("Setting up frontend...", bold=True)

        from webfluid.surface import setup_frontend
        setup_frontend(name)

        if skip_defaults: return

        conf = _frontend_conf()
        if _create_frontend(app_dir, conf, "fluid", name):
            node_cmd(
                ["npm", "install", "-w", "fluid/frontend"],
                project_root
            )

        (app_dir / "config.py").write_text(
            templates.app_config_py.format(
                name=name,
                frontend=json.dumps(
                    conf,
                    indent=2,
                    ensure_ascii=False
                )
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
            "wf": f">={version()}",
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
    base_import = ""
    import_base_fn = ""
    if as_base:
        manifest["type"] = "base"
        selected_base = questions.select_base()
        import_base_fn = "from webfluid.additives import import_base\n"
        base_import = f'\n\timport_base("{selected_base}"),'
        manifest["frontend"] = "none"
        index_html = templates.adtv_index1_html.format(
            name=manifest["name"]
        )
    else:
        manifest["type"] = "default"
        manifest["frontend"] = _frontend_conf()
        if _create_frontend(
                additive_root,
                manifest["frontend"],
                "additive",
                safe_id.replace("_", "-")
        ):
            index_html = templates.adtv_index2_html.format(
                name=manifest["name"]
            )
            node_cmd(
                ["npm", "install", "-w", f"additives/{safe_id}/frontend"],
                Path.cwd()
            )
        else:
            index_html = templates.adtv_index1_html.format(
                name=manifest["name"]
            )

    requirements = questions.requirements.ask()
    if requirements:
        copy = requirements.copy()
        requirements = [f"\t\t{r}," for r in copy]
        requirements_str = f"[\n{'\n'.join(requirements)}\t]"
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
        templates.app_py,
        templates.adtv_index_py,
        index_html
    )

    (additive_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False)
    )
    (additive_root / "__init__.py").write_text(
        templates.init_py.format(
            import_base=import_base_fn,
            base=base_import,
            requirements=requirements
        )
    )


def cli_entry(app: typer.Typer):
    app.add_typer(create, name="create")
