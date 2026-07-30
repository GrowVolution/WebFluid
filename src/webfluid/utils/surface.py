from pathlib import Path
from git import Repo, exc
import typer, shutil

from webfluid.core.constants import WF_STATIC
from webfluid.surface import dist
from webfluid.surface.src import htmx, alpine, vite, vite_dev, package_json
from webfluid.surface.wf_node import load_node
from webfluid.surface.wf_tailwind import load_tailwind
from webfluid.exceptions import FrontendException

_static_js = (Path(__file__).parent.parent / WF_STATIC.lstrip("/") / "js").resolve()


def setup_frontend(project):
    from .cli import download_file

    htmx_file = _static_js / "htmx.min.js"
    if not htmx_file.exists():
        download_file(htmx, htmx_file)
        if not htmx_file.exists():
            raise FrontendException("Failed to download htmx.min.js")

    alpine_file = _static_js / "alpine.min.js"
    if not alpine_file.exists():
        download_file(alpine, alpine_file)
        if not alpine_file.exists():
            raise FrontendException("Failed to download alpine.min.js")

    vite_dir = dist.parent / "vite"
    template_src = vite_dir / "packages" / "create-vite"
    template_dst = dist / "vite-templates"

    if not template_dst.exists() or not any(template_dst.iterdir()):
        typer.echo(typer.style(
            "Loading create-vite templates...", bold=True
        ))
        template_dst.mkdir(parents=True, exist_ok=True)

        try:
            Repo.clone_from(
                vite,
                vite_dir,
                branch="main",
                depth=1,
                filter="blob:none"
            )

            frameworks = (
                "lit", "preact", "qwik",
                "react", "solid", "svelte",
                "vanilla", "vue"
            )

            for framework in frameworks:
                for suffix in ("", "-ts"):
                    src = template_src / f"template-{framework}{suffix}"
                    if src.exists():
                        shutil.copytree(
                            src,
                            template_dst / f"{framework}{suffix}",
                            dirs_exist_ok=True
                        )

        except exc.GitCommandError:
            typer.echo(typer.style(
                "Failed to load vite from Github.",
                fg=typer.colors.RED, bold=True
            ))

        finally: shutil.rmtree(vite_dir, ignore_errors=True)

    load_node()
    load_tailwind()

    project_root = Path.cwd() / project

    package_json_file = project_root / "package.json"
    package_json_file.write_text(
        package_json.format(project=project)
    )

    vite_config_file = project_root / "vite.config.js"
    vite_config_file.write_text(vite_dev)


def validate_config(f):
    if "type" not in f:
        return False, "Frontend type not defined."

    t = f["type"]
    if t == "vite":
        if "framework" not in f:
            return False, "Frontend framework not defined."
        if f["framework"] not in ("lit", "none", "preact", "qwik",
                                  "react", "solid", "svelte", "vue"):
            return False, "Invalid frontend framework."
        if "typescript" in f and not isinstance(f["typescript"], bool):
            return False, "Invalid typescript value."
        if "register_index" in f and not isinstance(f["register_index"], bool):
            return False, "Invalid register_index value."

    elif t == "htmx":
        if "alpine" in f and not isinstance(f["alpine"], bool):
            return False, "Invalid alpine flag."

    elif t != "none": return False, "Invalid frontend type."

    return True, f
