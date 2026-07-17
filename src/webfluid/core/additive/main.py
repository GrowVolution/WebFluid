from fastapi.responses import HTMLResponse
from pathlib import Path

from webfluid.core.additive.router import Router
from webfluid.core.additive.version import Version
from webfluid.core.lifecycle import AdditiveLifecycle, RequestLifecycle
from webfluid.core.additive.lifecycle import install, configure, create_enable
from webfluid.core.additive.middleware import add_http_middleware
from webfluid.core.additive.processing import configure as configure_processing
from webfluid.core.additive.jinja import Jinja

from webfluid.surface.frontend import Frontend
from webfluid.utils.core import get_root_path
from webfluid.exceptions import AdditiveException, ManifestError


class Additive:
    def __init__(self, import_name, base=None, required_extensions=None):

        if not "additives." in import_name:
            raise AdditiveException("Additives have to be created inside the 'additives' package.")

        self.name = import_name.split(".")[-1]
        self.import_name = import_name
        self.root_path = Path(get_root_path(import_name)).resolve()

        from webfluid.core.additive.manifest import Manifest
        try: self.manifest = Manifest(self.root_path / "manifest.json")
        except (FileNotFoundError, ManifestError) as e:
            print(e)
            raise AdditiveException(f"[{self.name}] Failed to load manifest: {e}")

        if not "name" in self.manifest:
            self.manifest["name"] = self.name
        else:
            self.name = self.manifest["name"]
        self.id = self.manifest["id"]
        self.prefix = f"/{self.id.replace('_', '-')}"

        self.is_base = self.manifest["type"] == "base"
        self.required_extensions = required_extensions or []

        if base and self.is_base:
            raise AdditiveException(f"[{self.name}] Base additives cannot extend other additives.")
        elif base and not base.is_base:
            raise AdditiveException(f"[{self.name}] Default additives can only extend base additives.")

        self.base = base
        self.parent = None

        if base: self.required_extensions.extend(base.required_extensions or [])
        self.enable = create_enable(self)

        self._lifecycle = AdditiveLifecycle()
        self._request_lifecycle = RequestLifecycle()

        self._jinja = Jinja(self)

        if self.is_base:
            self.api = Router()
            self.app = Router(default_response_class=HTMLResponse)
            self.ws = Router()
            self.frontend = None
        else:
            self.api = Router(prefix="/api")
            self.app = Router(default_response_class=HTMLResponse)
            self.ws = Router(prefix="/ws")
            self.frontend = Frontend()

        add_http_middleware(self)
        configure_processing(self)

    def __repr__(self):
        return f"<{self.name} {self.version}> {self.manifest.get('description', '')}"

    def unique_name(self, name):
        if self.parent: return self.parent.unique_name(name)
        return f"{self.id}_{name}"

    @property
    def before_enable(self):
        return self._lifecycle.before_enable.add_hook

    @property
    def after_enable(self):
        return self._lifecycle.after_enable.add_hook

    @property
    def before_request(self):
        return self._request_lifecycle.before.add_hook

    @property
    def after_request(self):
        return self._request_lifecycle.after.add_hook

    @property
    def jinja_context(self):
        return self._jinja.context_dict

    @property
    def context_processor(self):
        return self._jinja.context.add_processor

    @property
    def render(self):
        return self._jinja.renderer.render

    @property
    def version(self):
        version_str = self.manifest["version"]
        return Version(*version_str.split("."))

    def install(self, _seen=None): install(self, _seen)
    def configure(self, config): configure(self, config)
