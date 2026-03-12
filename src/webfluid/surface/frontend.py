from fastapi import Request, Response, WebSocket
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from git import Repo, exc
from tqdm import tqdm
from markupsafe import Markup
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional, List, Callable
import typer, requests, shutil, httpx, websockets, asyncio,\
    subprocess, os, signal, json

from webfluid.core.constants import DEBUG, TAILWIND
from webfluid.surface import dist
from webfluid.surface.wf_node import load_node, _node_cmd, _node_env
from webfluid.surface.wf_tailwind import load_tailwind, generate_asset
from webfluid.utils import add_proxy, run_in_executor
from webfluid.exceptions import FrontendException

if TYPE_CHECKING:
    from webfluid import Fluid, Additive

_static_js = (Path(__file__).parent.parent / "app" / "static" / "js").resolve()

package_json = """
{{
    "name": "{project}",
    "version": "1.0.0",
    "private": true,
    "workspaces": [
      "additives/*/frontend"
    ],
    "scripts": {{
      "dev": "vite"
    }},
    "devDependencies": {{
      "vite": "^7.3.1"
    }}
}}
"""

vite_dev = """
import { defineConfig, mergeConfig, loadConfigFromFile } from "vite"
import fs from "fs"
import path from "path"

async function loadAdditiveConfigs(command: "serve" | "build") {
  const additivesDir = path.resolve(__dirname, "additives")
  const configs = []

  for (const name of fs.readdirSync(additivesDir)) {
    const configPath = path.join(additivesDir, name, "frontend", "vite.config.ts")

    if (!fs.existsSync(configPath)) continue

    const loaded = await loadConfigFromFile(
      { command, mode: "development" },
      configPath
    )

    if (!loaded?.config) continue

    const injected = mergeConfig(loaded.config, {
      base: `/${name}/`
    })

    configs.push(injected)
  }

  return configs
}

export default defineConfig(async ({ command }) => {
  const additiveConfigs = await loadAdditiveConfigs(command)

  let config = {}

  for (const c of additiveConfigs) {
    config = mergeConfig(config, c)
  }

  return config
})
"""
Manifest = Dict[str, ManifestChunk]

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

    if not template_dst.exists() or not any(template_dst.iterdir()):
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

    vite_config_file = Path.cwd() / "vite.config.js"
    vite_config_file.write_text(vite_dev)


def load_manifest(vite_dist: Path) -> Manifest:
    manifest_file = vite_dist / ".vite" / "manifest.json"
    if not manifest_file.exists():
        raise FrontendException("Failed to load Vites manifest.json")
    raw = json.loads(manifest_file.read_text())
    manifest: Manifest = {}

    for key, data in raw.items():
        manifest[key] = ManifestChunk(**data)

    return manifest


def resolve_entry(manifest: Manifest, entry: str):
    if entry not in manifest:
        raise FrontendException(f"'{entry}' not found in Vite manifest.")

    js_files = set()
    css_files = set()

    visited = set()
    def collect(chunk_name: str):
        if chunk_name in visited:
            return

        chunk = manifest.get(chunk_name)
        if not chunk:
            return
        visited.add(chunk_name)

        js_files.add(chunk.file)

        if chunk.css:
            css_files.update(chunk.css)

        if chunk.imports:
            for dep in chunk.imports:
                collect(dep)

    collect(entry)
    return list(js_files), list(css_files)


class Frontend:
    _static_js = "/wf-static/js"
    _proc: subprocess.Popen
    _dev_prefix = "/vite-dev"
    _static_files = {}

    htmx = f"{_static_js}/htmx.min.js"
    alpine = f"{_static_js}/alpine.min.js"

    def __init__(self, additive: "Additive | None" = None):
        self.type = "none"
        self.framework = "none"
        self.typescript = False
        self.alpine = False
        self.prefix: str
        self.dist: Path
        self.main: str
        self.manifest: Manifest
        self.generate_tailwind: Callable

        if additive is not None: self.init_additive(additive)

    def init_additive(self, additive: "Additive"):
        frontend = additive.manifest["frontend"]
        self.type = frontend["type"]
        self.framework = frontend.get("framework", self.framework)
        self.typescript = frontend.get("typescript", self.typescript)
        self.alpine = frontend.get("alpine", self.alpine)
        self.prefix = additive.prefix

        if self.type == "vite":
            self.dist = additive.root_path / "frontend" / "dist"
            src = self.dist.parent / "src"
            for name in ("main.js","main.jsx","main.ts","main.tsx"):
                if (src / name).exists():
                    self.main = name
                    break

            self.generate_tailwind = (
                lambda: generate_asset(
                    src / "tailwind_raw.css",
                    src / "tailwind.css",
                    self.dist.parent
                )
            )

            if not DEBUG:
                self.manifest = load_manifest(self.dist)
                Frontend._static_files[f"{additive.name}_frontend"] = (
                    self.prefix, StaticFiles(directory=self.dist)
                )

            if TAILWIND: self.generate_tailwind()

    def scripts(self) -> Markup:
        template = ""
        if self.type == "htmx":
            template += f'<script src="{self.htmx}"></script>\n'
            if self.alpine: template += f'<script src="{self.alpine}" defer></script>\n'

        if self.type == "vite":
            if DEBUG:
                if TAILWIND: self.generate_tailwind()
                template += f'<script type="module" src="{self._dev_prefix}/@vite/client"></script>\n'

            if not hasattr(self, "main"):
                raise FrontendException("Missing main entry in frontend/src.")
            template += self.vite(f"src/{self.main}")

        if TAILWIND:
            template += f'<link rel="stylesheet" href="/wf-static/css/tailwind.css">\n'
            template += f'<link rel="stylesheet" href="/static/css/tailwind.css">\n'
            template += f'<link rel="stylesheet" href="{self.prefix}/static/css/tailwind.css">'

        return Markup(template)

    def vite(self, entry: str) -> Markup:
        if self.type != "vite": return ""

        if DEBUG:
            if entry.endswith(".js") or entry.endswith(".ts"):
                return Markup(
                    f'<script type="module" src="{self._dev_prefix}{self.prefix}/{entry}"></script>'
                )
            elif entry.endswith(".css"):
                return Markup(
                    f'<link rel="stylesheet" href="{self._dev_prefix}{self.prefix}/{entry}">'
                )
            return ""

        js, css = resolve_entry(self.manifest, entry)
        tags = []

        for file in js:
            tags.append(f'<script type="module" src="{self.prefix}/{file}"></script>')
        for file in css:
            tags.append(f'<link rel="stylesheet" href="{self.prefix}/{file}">')

        return Markup("\n".join(tags))

    @classmethod
    def run(cls, fluid: "Fluid"):
        if DEBUG:
            cls._proc = subprocess.Popen(
                [_node_cmd("npm"), "run", "dev"],
                cwd=fluid.app_root,
                env=_node_env(),
                start_new_session=True
            )
            fluid.shutdown_hook(cls.stop)
            add_proxy(
                fluid, "http://localhost:5173",
                prefix=self._dev_prefix
            )
        else:
            cls._proc = subprocess.Popen(
                [_node_cmd("npm"), "run", "build", "--workspaces"],
                cwd=fluid.app_root,
                env=_node_env(),
                capture_output=True,
                text=True
            )
            async def join_later():
                code = cls._proc.poll()
                if code is None:
                    code = await run_in_executor(cls._proc.wait)
                if code != 0:
                    raise FrontendException(cls._proc.stderr or cls._proc.stdout)
            fluid.startup_hook(join_later)
            for name, data in cls._static_files.items():
                fluid.mount(data[0], data[1], name)

    @classmethod
    def stop(cls):
        if DEBUG and cls._proc.poll() is None:
            os.killpg(cls._proc.pid, signal.SIGINT)
            cls._proc.wait(.5)
            if cls._proc.poll() is None:
                os.killpg(cls._proc.pid, signal.SIGKILL)
                cls._proc.wait()


@dataclass
class ManifestChunk:
    src: Optional[str] = None
    file: str = ""
    css: Optional[List[str]] = None
    assets: Optional[List[str]] = None
    isEntry: bool = False
    name: Optional[str] = None
    isDynamicEntry: bool = False
    imports: Optional[List[str]] = None
    dynamicImports: Optional[List[str]] = None
