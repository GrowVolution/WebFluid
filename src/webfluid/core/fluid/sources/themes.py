from markupsafe import Markup

from webfluid.core.constants import THEMES, FRAMEWORK_STATIC
from webfluid.core.context import FluidContext
from webfluid.core.identity import FRAMEWORK_ID
from webfluid.exceptions import FrameworkException
from webfluid.utils.logging import factory as log_factory

_SURFACES = Markup(f'<link rel="stylesheet" href="{FRAMEWORK_STATIC}/css/surfaces.css">')


class Themes:
    def __init__(self, fluid):
        self.fluid = fluid
        self.themes = {}
        if THEMES:
            self.themes[FRAMEWORK_ID] = Markup(
                f'<link rel="stylesheet" href="{FRAMEWORK_STATIC}/css/theme.css">'
            )

        self.global_theme = fluid.config["GLOBAL_THEME"]

    def _validate(self, name, exists):
        if not THEMES: raise FrameworkException("Themes are not enabled.")

        elif not exists and name in self.themes:
            raise FrameworkException(f"Theme '{name}' already exists.")
        elif exists and name not in self.themes:
            raise FrameworkException(f"Theme '{name}' does not exist.")

    def _selected(self, name=None):
        if name is None:
            ctx = FluidContext.try_current()
            request = ctx.request if ctx is not None else None
            name = request.session.get("theme") if request is not None else None

        selected = self.themes.get(name or self.global_theme) or self.themes[FRAMEWORK_ID]
        return _SURFACES + "\n" + selected

    def _read(self, markup, scheme):
        from .variables import stylesheets, variables

        paths = []
        for href in stylesheets(markup):
            path = self.fluid.static_files.resolve(href)
            if path is None: log_factory.warning(f"Theme stylesheet '{href}' is not a local static file.")
            else: paths.append(path)
        return variables(paths, scheme)

    def add(self, name, link):
        self._validate(name, False)
        self.themes[name] = link if isinstance(link, Markup) else Markup(link)

    def get(self):
        if not THEMES: raise FrameworkException("Themes are not enabled.")
        return self._selected()

    def set(self, request, name):
        self._validate(name, True)
        request.session["theme"] = name

    def variables(self, name=None, scheme=None):
        if not THEMES: return {}

        try: return self._read(self._selected(name), scheme)
        except Exception as exc:
            log_factory.warning(f"Theme variables are unavailable: {type(exc).__name__}: {exc}")
            return {}
