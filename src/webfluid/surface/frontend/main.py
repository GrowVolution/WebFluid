from fastapi import HTTPException
from markupsafe import Markup
from datetime import datetime, UTC

from .vite import Vite
from webfluid.core.constants import (
    DEBUG, TAILWIND, WF_STATIC, THEMES, FRAMEWORK_ID
)
from webfluid.surface.wf_tailwind import generate_asset

_static_js = f"{WF_STATIC}/js"


class Frontend:
    htmx = f"{_static_js}/htmx.min.js"
    alpine = f"{_static_js}/alpine.min.js"

    def __init__(self, fluid=None, additive=None):
        self.type = "none"
        self.alpine = False

        self.prefix = "/frontend"
        self.rel = FRAMEWORK_ID + self.prefix
        self.tailwind = ""

        if fluid is not None: self.cover_fluid(fluid)
        if additive is not None: self.cover_additive(additive)

    def _init(self, frontend, root_path, name="app"):
        self.type = frontend["type"]
        self.alpine = frontend.get("alpine", self.alpine)

        raw_tailwind = f"tailwind{'_raw' if THEMES else '_no_themes'}.css"
        static = root_path / "static" / "css"
        def generate_tailwind(f, s):
            if f and hasattr(self, "_vite"):
                self._vite.generate_tailwind(raw_tailwind)

            if s:
                generate_asset(
                    static / raw_tailwind,
                    static / "tailwind.css",
                    root_path
                )

        self.generate_tailwind = generate_tailwind

        if self.type == "vite":
            self._vite = Vite(root_path / "frontend", self.rel, frontend)
            if not DEBUG: self._vite.add_static(name, self.prefix)
            if TAILWIND: self.generate_tailwind(True, False)

        if TAILWIND and (root_path / "static" / "css" / raw_tailwind).exists():
            self.tailwind = (
                f"{self.prefix.removesuffix("/frontend")}/static/css/tailwind.css"
            )

    def cover_fluid(self, fluid):
        self._init(
            fluid.config["APP_FRONTEND"],
            fluid.project_root / "fluid"
        )

        if hasattr(self, "_vite"): self._vite.register(fluid)

    def cover_additive(self, additive):
        self.prefix = additive.prefix + self.prefix
        self.rel = f"additives/{additive.root_path.name}/frontend"
        self._init(
            additive.manifest["frontend"],
            additive.root_path,
            additive.id
        )

        if hasattr(self, "_vite"): self._vite.register(additive.app)

    def include(self):
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
        has_vite = hasattr(self, "_vite")
        if not has_vite: raise HTTPException(404)

        if DEBUG: self.generate_tailwind(True, True)
        return await self._vite.response()

    @classmethod
    def prepare(cls, fluid): Vite.prepare(fluid)
