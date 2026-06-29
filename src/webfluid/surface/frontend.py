from fastapi import Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
from git import Repo, exc
from tqdm import tqdm
from markupsafe import Markup
from selectolax.lexbor import LexborHTMLParser, create_tag
from mimetypes import guess_type
from datetime import datetime, UTC
from typing import TYPE_CHECKING, Callable
import typer, requests, shutil, subprocess, os, signal

from webfluid.core.context import FluidContext
from webfluid.core.constants import DEBUG, TAILWIND, WF_STATIC, THEMES, PROCESSING
from webfluid.surface import dist
from webfluid.surface.src import htmx, alpine, vite, vite_dev, package_json
from webfluid.surface.wf_node import load_node, node_proc, node_cmd
from webfluid.surface.wf_tailwind import load_tailwind, generate_asset
from webfluid.utils.core import add_proxy, run_in_executor, get_proxy
from webfluid.exceptions import FrontendException, NodeError

if TYPE_CHECKING:
    from webfluid import Fluid, Additive

_static_js = (Path(__file__).parent.parent / "fluid" / "static" / "js").resolve()


def _download_file(url: str, dest: Path):
    typer.secho(f"Downloading '{url}'...", bold=True)
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

    load_node(_download_file)
    load_tailwind(_download_file)

    project_root = Path.cwd() / project

    package_json_file = project_root / "package.json"
    package_json_file.write_text(
        package_json.format(project=project)
    )

    vite_config_file = project_root / "vite.config.js"
    vite_config_file.write_text(vite_dev)


def validate_config(f: dict) -> tuple[bool, str | dict]:
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


class Frontend:
    _static_js = f"{WF_STATIC}/js"
    _app_root: Path
    _proc: subprocess.Popen
    _dev_server = "http://localhost:5173"
    _dev_prefix = "/vite-dev"
    _static_files = {}

    htmx = f"{_static_js}/htmx.min.js"
    alpine = f"{_static_js}/alpine.min.js"

    def __init__(
            self,
            fluid: "Fluid | None" = None,
            additive: "Additive | None" = None
    ):
        self.type = "none"
        self.framework = "none"
        self.typescript = False
        self.register_index = True
        self.alpine = False
        self.prefix: str
        self.root: Path
        self.dist: Path
        self.rel: str
        self.generate_tailwind: Callable
        self.tailwind: str

        if fluid is not None: self.cover_fluid(fluid)
        if additive is not None: self.cover_additive(additive)

    def _init(self, frontend: dict, root_path: Path, name: str = "app"):
        self.type = frontend["type"]
        self.framework = frontend.get("framework", self.framework)
        self.typescript = frontend.get("typescript", self.typescript)
        self.register_index = frontend.get("register_index", self.register_index)
        self.alpine = frontend.get("alpine", self.alpine)

        raw_tailwind = f"tailwind{'_raw' if THEMES else '_no_themes'}.css"
        frontend_path = root_path / "frontend"
        static = root_path / "static" / "css"
        def generate_tailwind(f, s):
            if f:
                generate_asset(
                    src / raw_tailwind,
                    src / "tailwind.css",
                    getattr(self, "root", frontend_path)
                )

            if s:
                generate_asset(
                    static / raw_tailwind,
                    static / "tailwind.css",
                    root_path
                )

        self.generate_tailwind = generate_tailwind

        if self.type == "vite":
            self.root = frontend_path
            self.dist = self.root / "dist"
            src = self.root / "src"

            if not DEBUG:
                self.dist.mkdir(parents=True, exist_ok=True)
                Frontend._static_files[f"{name}_frontend"] = (
                    self.prefix, StaticFiles(directory=self.dist)
                )

            if TAILWIND: self.generate_tailwind(True, False)

        if TAILWIND:
            if not (root_path / "static" / "css" / "tailwind_raw.css").exists():
                self.tailwind = ""
                return

            self.tailwind = (
                f"{self.prefix.removesuffix("/frontend")}/static/css/tailwind.css"
            )

    async def _updated_index(self, index: str) -> str:
        try: ctx = FluidContext.current()
        except RuntimeError: return index
        html = LexborHTMLParser(index)

        if DEBUG:
            for script in html.css("script"):
                src_old = script.attributes.get("src")
                if src_old is None: continue
                script.attrs["src"] = f"{Frontend._dev_prefix}/{self.rel}{src_old}"

            for link in html.css("link"):
                href_old = link.attributes.get("href")
                if href_old is None: continue
                href_old = href_old.lstrip("/")
                if (self.root / "public" / href_old).exists():
                    link.attrs["href"] = f"{Frontend._dev_prefix}/{self.rel}/public/{href_old}"
                else:
                    link.attrs["href"] = f"{Frontend._dev_prefix}/{self.rel}/{href_old}"

            client = create_tag("script")
            client.attrs["type"] = "module"
            client.attrs["src"] = f"{Frontend._dev_prefix}/@vite/client"
            html.head.insert_child(client)

            if self.framework == "react":
                refresh = create_tag("script")
                refresh.attrs["type"] = "module"
                refresh.insert_child(f"""
                    import RefreshRuntime from "{Frontend._dev_prefix}/@react-refresh";
                    RefreshRuntime.injectIntoGlobalHook(window);
                    window.$RefreshReg$ = () => {{}};
                    window.$RefreshSig$ = () => (type) => type;
                    window.__vite_plugin_react_preamble_installed__ = true;
                """)
                html.head.insert_child(refresh)

        theme = ctx.fluid.get_theme() if THEMES else ""
        if PROCESSING:
            src = await ctx.fluid.render(
                f"{theme}" + "{{ src() }}",
                is_string=True
            )

        else: src = "\n\t".join([theme, *ctx.fluid.sources])

        node = LexborHTMLParser(src).head
        if node: html.head.insert_child(node)

        return html.html

    async def _vite(self) -> str:
        if self.type != "vite": return ""

        if DEBUG:
            if TAILWIND: self.generate_tailwind(True, True)
            index_file = self.root / "index.html"
        else: index_file = self.dist / "index.html"

        return await self._updated_index(
            index_file.read_text()
        )

    def cover_fluid(self, fluid: "Fluid"):
        self.prefix = "/frontend"
        self.rel = f"fluid{self.prefix}"
        self._init(
            fluid.config["APP_FRONTEND"],
            fluid.app_root / "fluid"
        )

        if self.type == "vite" and self.register_index:
            fluid.get("/")(self.vite)

    def cover_additive(self, additive: "Additive"):
        self.prefix = f"{additive.prefix}/frontend"
        self.rel = f"additives/{additive.root_path.name}/frontend"
        self._init(
            additive.manifest["frontend"],
            additive.root_path,
            additive.id
        )

        if self.type == "vite" and self.register_index:
            additive.app.get("/")(self.vite)

    def include(self) -> Markup:
        template = ""
        if self.type == "htmx":
            template += f'<script src="{Frontend.htmx}"></script>\n'
            if self.alpine: template += f'<script src="{Frontend.alpine}" defer></script>\n'

        if TAILWIND:
            if DEBUG:
                self.generate_tailwind(False, True)
                src = self.tailwind + f"?t={datetime.now(UTC).timestamp()}"
            else: src = self.tailwind
            template += f'<link rel="stylesheet" href="{src}">\n'

        return Markup(template)

    async def vite(self):
        response = HTMLResponse(await self._vite())
        response.set_cookie("vite_ns", self.rel)
        return response

    @classmethod
    def prepare(cls, fluid: "Fluid"):
        if DEBUG:
            def create_proc():
                cls._proc = node_proc(
                    ["node", "node_modules/vite/bin/vite.js"],
                    fluid.app_root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )

            add_proxy(
                fluid, cls._dev_server,
                prefix=cls._dev_prefix,
                pass_prefix=True
            )
            fluid.shutdown_hook(cls.stop)

        else:
            async def create_proc():
                try:
                    node_cmd(
                        ["npm", "run", "check", "--workspaces"],
                        fluid.app_root
                    )
                except NodeError as e:
                    if "No workspaces found!" not in str(e):
                        raise e

                cls._proc = node_proc(
                    ["npm", "run", "build", "--workspaces"],
                    fluid.app_root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                out, err = await run_in_executor(cls._proc.communicate)
                if cls._proc.returncode != 0:
                    msg = err or out or "Unknown error"
                    if "No workspaces found!" not in msg:
                        raise FrontendException(msg)

            def mount():
                for name, data in cls._static_files.items():
                    fluid.mount(data[0], data[1], name)
            fluid.startup_hook(mount)

        if (fluid.app_root / "package.json").exists():
            fluid.startup_hook(create_proc)

        cls._app_root = fluid.app_root
        fluid.startup_hook(lambda: fluid.get(
            "/{path:path}", name="vite_asset_catch"
        )(cls._asset_catch))

    @classmethod
    def stop(cls):
        proc = cls._proc

        if not DEBUG or proc.poll() is not None:
            return

        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            proc.wait()
        else:
            os.killpg(proc.pid, signal.SIGINT)

            try: proc.wait(0.5)
            except subprocess.TimeoutExpired:
                pass

            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()

    @classmethod
    async def _asset_catch(cls, request: Request, path: str):
        if path.startswith(("api", "wf-static")) or "/frontend" in path:
            return Response(status_code=404)

        if "." not in path:
            return Response(status_code=404)

        if path.startswith("."):
            if not DEBUG:
                return Response(status_code=404)
            final_path = path
        else:
            vite_ns = request.cookies.get("vite_ns")
            if vite_ns is None: return Response(status_code=404)

            if (cls._app_root / vite_ns / path).exists():
                final_path = f"{vite_ns}/{path}"

            elif (cls._app_root / vite_ns / "public" / path).exists():
                final_path = f"{vite_ns}/public/{path}"

            else: return Response(status_code=404)

        if DEBUG:
            proxy = get_proxy(
                cls._dev_server,
                prefix=cls._dev_prefix,
                pass_prefix=True
            )

            return await proxy(request, final_path)

        file = cls._app_root / final_path
        return FileResponse(
            file,
            filename=file.name,
            media_type=guess_type(file)[0]
                       or "application/octet-stream"
        )
