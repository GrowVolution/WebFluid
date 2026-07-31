from fastapi import FastAPI
from pathlib import Path
from warnings import warn
import os

from webfluid.core.fluid import middleware
from webfluid.core.lifecycle import FluidLifecycle, RequestLifecycle
from webfluid.core.fluid.frontend import setup_frontend
from webfluid.core.fluid.extensions import enable_extensions
from webfluid.core.fluid.ratelimit import Limiter
from webfluid.core.fluid.jinja import Jinja
from webfluid.core.fluid.routing import Routes
from webfluid.core.fluid.static import StaticFiles, StaticPrefixes
from webfluid.core.fluid.sources import Sources, Themes
from webfluid.core.fluid.server import Server

from webfluid.core.config.main import Config
from webfluid.core.config.init import init_configs
from webfluid.core.config.build import build_config

from webfluid.core.constants import (
    APP_STATIC, FRAMEWORK_STATIC, PROCESSING, ADDITIVES
)
from webfluid.core.identity import FRAMEWORK_NAME
from webfluid.core.processing import setup_processing
from webfluid.surface.frontend import Frontend
from webfluid.utils.core import (
    get_root_path, safe_string,
    close_proxy_client
)
from webfluid.utils.additives import register_additives
from webfluid.exceptions import FrameworkException

_moved = { "app_root": "project_root" }


class Fluid(FastAPI):
    def __init__(self, import_name):
        self.project_root = Path(get_root_path(import_name)).resolve()
        self.additive_root = self.project_root / "additives"

        init_configs(self)
        self.config = Config()
        self.config.update(build_config())

        if not self.config.get("SECRET_KEY"):
            raise FrameworkException("SECRET_KEY is required.")

        self.name = safe_string(os.getenv("APP_NAME", import_name)).lower()
        super().__init__(**self.config.get("APP_CONFIG", {}))

        self._build_lifecycle()
        self._build_rendering()
        self._build_static()
        self._build_serving()
        self._build_features()
        self._build_middleware()

    def __repr__(self):
        from webfluid import version
        return f"<{FRAMEWORK_NAME} {version()}>"

    def __getattr__(self, name):
        moved = _moved.get(name)
        if moved is None: raise AttributeError(name)

        warn(
            f"Fluid.{name} is deprecated, use Fluid.{moved} instead.",
            DeprecationWarning, stacklevel=2
        )
        return getattr(self, moved)

    def _build_lifecycle(self):
        self._lifecycle = FluidLifecycle()
        self._request_lifecycle = RequestLifecycle()
        self._routes = Routes(self)

    def _build_rendering(self):
        self._jinja = Jinja(self)
        self._sources = Sources()
        self._themes = Themes(self)

        self.add_source(
            f'<script src="{FRAMEWORK_STATIC}/js/base.js" type="module"></script>',
            priority=5
        )

    def _build_static(self):
        self.static_files = StaticFiles(self)
        self.static_prefixes = StaticPrefixes(
            APP_STATIC, FRAMEWORK_STATIC,
            "/frontend", "/vite-dev"
        )

    def _build_serving(self):
        self._limiter = Limiter(self)
        self._server = Server(self, self._lifecycle)

    def _build_features(self):
        if ADDITIVES: self.startup_hook(
            lambda: register_additives(self)
        )

        enable_extensions(self)
        setup_frontend(self)

        self.startup_hook(self._prepare)
        Frontend.prepare(self)

    def _build_middleware(self):
        middleware.request.add(self, self._request_lifecycle)
        middleware.session.add(self)

        if PROCESSING: setup_processing(self)

        self.shutdown_hook(close_proxy_client)

    async def _prepare(self):
        self.static_prefixes.freeze()
        self.static_files.mount(self)
        self._sources.freeze()
        middleware.proxy_headers.add(self)
        self._jinja.prepare()

    def url_path_for(self, name, /, **path_params):
        return self._routes.url_path_for(name, **path_params)

    @property
    def startup_hook(self):
        return self._lifecycle.startup.add

    @property
    def shutdown_hook(self):
        return self._lifecycle.shutdown.add

    @property
    def before_request(self):
        return self._request_lifecycle.before.add

    @property
    def after_request(self):
        return self._request_lifecycle.after.add

    @property
    def add_template_loader(self):
        return self._jinja.loaders.add

    @property
    def jinja_env(self):
        return self._jinja.env

    @property
    def context_processor(self):
        return self._jinja.context.add_processor

    @property
    def render(self):
        return self._jinja.renderer.render

    @property
    def render_string(self):
        return self._jinja.renderer.render_string

    @property
    def add_source(self):
        return self._sources.add

    @property
    def sources(self):
        return self._sources.sources

    @property
    def rendered_sources(self):
        return self._sources.rendered

    @property
    def add_theme(self):
        return self._themes.add

    @property
    def get_theme(self):
        return self._themes.get

    @property
    def set_theme(self):
        return self._themes.set

    @property
    def limit(self):
        return self._limiter.limit

    @property
    def mix(self):
        return self._server.run
