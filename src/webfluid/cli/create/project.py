from pathlib import Path
import typer, shutil

from .helpers import make_defaults, frontend_conf, create_frontend
from webfluid.cli.create import templates
from webfluid.core.identity import FRAMEWORK_ID
from webfluid.surface import node_cmd
from webfluid.utils.surface import setup_frontend


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

    app_dir = project_root / FRAMEWORK_ID

    if not skip_defaults:
        typer.secho("Generating default structure...",
                    bold=True)

        make_defaults(
            app_dir,
            templates.api_router_py,
            templates.app_v1_py,
            templates.app_router_py,
            templates.app_index_py
        )

        (project_root / "additives").mkdir(exist_ok=True)
        (project_root / ".gitignore").write_text(
            templates.app_gitignore, encoding="utf-8"
        )

    def frontend():
        typer.secho("Setting up frontend...", bold=True)
        setup_frontend(name)

        if skip_defaults: return

        conf = frontend_conf()
        if create_frontend(app_dir, conf, FRAMEWORK_ID, name):
            node_cmd(
                ["npm", "install"],
                project_root
            )
            node_cmd(
                ["npm", "install", "-w", f"{FRAMEWORK_ID}/frontend"],
                project_root
            )

            shutil.rmtree(app_dir / "app", ignore_errors=True)
            (project_root / "main.py").write_text(
                templates.main_py.format(index=""),
                encoding="utf-8"
            )
        else:
            node_cmd(
                ["npm", "install"],
                project_root
            )

            (app_dir / "templates/index.html").write_text(
                templates.app_index_html, encoding="utf-8"
            )
            (project_root / "main.py").write_text(
                templates.main_py.format(
                    index=f"""
    from {FRAMEWORK_ID}.app import app_router
    app.include_router(app_router)
                """), encoding="utf-8"
            )

        conf_list = str(conf).strip("{}").split(", ")
        conf_str = ("{\n\t\t"
                    f"{',\n\t\t'.join(conf_list)}"
                    "\n\t}")
        (app_dir / "config.py").write_text(
            templates.app_config_py.format(
                name=name,
                frontend=conf_str
            ), encoding="utf-8"
        )

    if not skip_frontend: frontend()

    if babel_fallback:
        typer.secho("Extracting Babel fallback catalogs...",
                    bold=True)

        from webfluid.extensions.babel.main import CLIExtension
        CLIExtension.extract_fallback(project_root)
        CLIExtension.compile_fallback(project_root)

    typer.secho(f"Successfully created project '{name}'.",
                bold=True, fg=typer.colors.GREEN)
