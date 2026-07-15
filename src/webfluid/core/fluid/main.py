from fastapi import FastAPI
from pathlib import Path
import os

from webfluid.core.fluid import middleware
from webfluid.core.fluid.lifecycle import AppLifecycle, RequestLifecycle
from webfluid.core.fluid.frontend import setup_frontend
from webfluid.core.fluid.extensions import enable_extensions
from webfluid.core.fluid.ratelimit import Limiter
from webfluid.core.fluid.jinja import Jinja
from webfluid.core.fluid.static import StaticFiles, StaticPrefixes
from webfluid.core.fluid.sources import Sources, Themes
from webfluid.core.fluid.server import Server

from webfluid.core.config import Config, init_configs, build_config
from webfluid.core.constants import (
    APP_STATIC, WF_STATIC, PROCESSING, ADDITIVES
)
from webfluid.core.processing import setup_processing
from webfluid.surface.frontend import Frontend
from webfluid.utils.core import (
    get_root_path, safe_string,
    close_proxy_client
)
from webfluid.utils.additives import register_additives
from webfluid.exceptions import FrameworkException


class Fluid(FastAPI):
    def __init__(self, import_name):
        init_configs(self)
        self.config = Config()
        self.config.from_object(build_config())

        if not self.config.get("SECRET_KEY"):
            raise FrameworkException("SECRET_KEY is required.")

        self.name = safe_string(os.getenv("APP_NAME", import_name)).lower()
        super().__init__(**self.config.get("APP_CONFIG", {}))

        self.app_root = Path(get_root_path(import_name)).resolve()
        self.additive_root = self.app_root / "additives"

        self.static_files = StaticFiles(self)
        self.static_prefixes = StaticPrefixes(
            APP_STATIC, WF_STATIC,
            "/frontend", "/vite-dev"
        )

        self._app_lifecycle = AppLifecycle()
        self._request_lifecycle = RequestLifecycle()

        self._jinja = Jinja(self)
        self._sources = Sources()
        self._themes = Themes(self)
        self._limiter = Limiter(self)
        self._server = Server(self)

        self.add_source(
            f'<script src="{WF_STATIC}/js/base.js" type="module"></script>',
            priority=5
        )

        if ADDITIVES: self.startup_hook(
            lambda: register_additives(self)
        )

        enable_extensions(self)
        setup_frontend(self)

        self.startup_hook(self._prepare)
        Frontend.prepare(self)

        middleware.http.add(self)
        middleware.session.add(self)

        if PROCESSING: setup_processing(self)

        self.shutdown_hook(close_proxy_client)

    def __repr__(self):
        from webfluid import version
        return f"<WebFluid {version()}>"

    async def _prepare(self):
        self.static_prefixes.freeze()
        self.static_files.mount(self)
        self._sources.freeze()
        middleware.proxy_headers.add(self)
        self._jinja.prepare()

    @property
    def startup_hook(self):
        return self._app_lifecycle.startup.add_hook

    @property
    def shutdown_hook(self):
        return self._app_lifecycle.shutdown.add_hook

    @property
    def before_request(self):
        return self._request_lifecycle.before.add_processor

    @property
    def after_request(self):
        return self._request_lifecycle.after.add_processor

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
    def add_source(self):
        return self._sources.add

    @property
    def sources(self):
        return self._sources.sources

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
