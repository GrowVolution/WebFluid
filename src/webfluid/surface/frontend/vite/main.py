from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .index import manipulate_index
from .assets import asset_catch
from webfluid.core.constants import DEBUG
from webfluid.surface.wf_tailwind import generate_asset


class Vite:
    _static_files = {}

    def __init__(self, root_path, relative_path, config):
        self.root = root_path
        self.rel= relative_path
        self.dist = root_path / "dist"
        self.src = root_path / "src"

        self.framework = config.get("framework", "none")
        self.typescript = config.get("typescript", False)
        self.register_index = config.get("register_index", True)

    async def index(self):
        if DEBUG: index_file = self.root / "index.html"
        else: index_file = self.dist / "index.html"

        return await manipulate_index(
            self.root,
            self.rel,
            self.framework,
            index_file.read_text()
        )

    async def response(self):
        response = HTMLResponse(await self.index())
        response.set_cookie("vite_ns", self.rel)
        return response

    def add_static(self, name, prefix):
        self.dist.mkdir(parents=True, exist_ok=True)
        Vite._static_files[f"{name}_frontend"] = (
            prefix, StaticFiles(directory=self.dist)
        )

    def generate_tailwind(self, raw_tailwind):
        generate_asset(
            self.src / raw_tailwind,
            self.src / "tailwind.css",
            self.root
        )

    def register(self, target):
        if self.register_index:
            target.get("/")(self.response)

    @classmethod
    def prepare(cls, fluid):
        if DEBUG:
            from .dev import startup_hook

        else:
            def mount():
                for name, data in cls._static_files.items():
                    fluid.mount(data[0], data[1], name)
            fluid.startup_hook(mount)

            from .prod import startup_hook

        if (fluid.project_root / "package.json").exists():
            fluid.startup_hook(startup_hook(fluid))

        fluid.startup_hook(lambda: fluid.get(
            "/{path:path}", name="vite_asset_catch"
        )(asset_catch(fluid.project_root)))
