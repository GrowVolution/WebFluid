from markupsafe import Markup

from webfluid.core.constants import THEMES, FRAMEWORK_ID, WF_STATIC
from webfluid.core.context import FluidContext
from webfluid.exceptions import FrameworkException


class Themes:
    def __init__(self, fluid):
        self.themes = {}
        if THEMES:
            self.themes[FRAMEWORK_ID] = Markup(
                f'<link rel="stylesheet" href="{WF_STATIC}/css/theme.css">'
            )

        self.global_theme = fluid.config["GLOBAL_THEME"]

    def _validate(self, name, exists):
        if not THEMES: raise FrameworkException("Themes are not enabled.")

        elif not exists and name in self.themes:
            raise FrameworkException(f"Theme '{name}' already exists.")
        elif exists and name not in self.themes:
            raise FrameworkException(f"Theme '{name}' does not exist.")

    def add(self, name, link):
        self._validate(name, False)
        self.themes[name] = link

    def get(self):
        if not THEMES: raise FrameworkException("Themes are not enabled.")

        ctx = FluidContext.try_current()
        theme = ctx.request.session.get("theme") if ctx and ctx.request else None
        return self.themes.get(theme or self.global_theme) \
            or self.themes[FRAMEWORK_ID]

    def set(self, request, name):
        self._validate(name, True)
        request.session["theme"] = name
