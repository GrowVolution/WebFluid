from pathlib import Path
from git import Repo, exc
from tqdm import tqdm
import typer, requests, shutil

from webfluid.surface import dist
from webfluid.surface.wf_node import load_node
from webfluid.surface.wf_tailwind import load_tailwind
from webfluid.exceptions import FrontendException

_static_js = (Path(__file__).parent.parent / "app" / "static" / "js").resolve()

package_json = """
{{
    "name": "{project}",
    "version": "1.0.0",
    "private": true,
    "workspaces": [
    "additives/*/frontend"
    ]
}}
"""

htmx = "https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js"
alpine = "https://cdn.jsdelivr.net/npm/alpinejs@3.15.8/dist/cdn.min.js"
vite = "https://github.com/vitejs/vite.git"


def _download_file(url: str, dest: Path):
    typer.echo(typer.style(f"Downloading '{url}'...", bold=True))
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
                total=total if total > 0 else None, unit="B",
                unit_scale=True, desc=str(dest)
        ) as bar:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))


def setup_frontend(project: str):
    htmx_file = _static_js / "htmx.min.js"
    if not htmx_file.exists():
        _download_file(htmx, htmx_file)
        if not htmx_file.exists():
            raise FrontendException("Failed to download htmx.min.js")

    alpine_file = _static_js / "alpine.min.js"
    if not alpine_file.exists():
        _download_file(alpine, alpine_file)
        if not alpine_file.exists():
            raise FrontendException("Failed to download alpine.min.js")

    vite_dir = dist.parent / "vite"
    template_src = vite_dir / "packages" / "create-vite"
    template_dst = dist / "vite-templates"

    if not (template_dst.exists() or any(template_dst.iterdir())):
        typer.echo(typer.style("Loading create-vite templates...", bold=True))
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

    load_node(_download_file)
    load_tailwind(_download_file)

    package_json_file = Path.cwd() / "package.json"
    package_json_file.write_text(package_json.format(project=project))
