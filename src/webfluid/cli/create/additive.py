from pathlib import Path
import typer, json, shutil

from .helpers import frontend_conf, create_frontend, make_defaults
from webfluid.cli import questions
from webfluid.cli.create import templates
from webfluid.core.constants import FRAMEWORK_ID
from webfluid.surface import node_cmd
from webfluid.utils.core import safe_string


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

        manifest["frontend"] = frontend_conf()
        if create_frontend(
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

    make_defaults(
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
