from fastapi.responses import HTMLResponse
from jinja2 import ChoiceLoader, FileSystemLoader, PrefixLoader

from .router import Router
from webfluid.exceptions import AdditiveException


class BaseKind:
    is_base = True

    def routers(self):
        return (
            Router(),
            Router(default_response_class=HTMLResponse),
            Router()
        )

    def frontend(self): return None

    def loader(self, additive): return None

    def check_enable(self, additive):
        raise AdditiveException(
            f"[{additive.name}] Base additives are not allowed be enabled."
        )


class FeatureKind:
    is_base = False

    def routers(self):
        return (
            Router(prefix="/api"),
            Router(default_response_class=HTMLResponse),
            Router(prefix="/ws")
        )

    def frontend(self):
        from webfluid.surface.frontend import Frontend
        return Frontend()

    def loader(self, additive):
        templates = FileSystemLoader(additive.root_path / "templates")
        if additive.base:
            templates = ChoiceLoader([
                templates,
                FileSystemLoader(additive.base.root_path / "templates")
            ])
        return PrefixLoader({ additive.id: templates })

    def check_enable(self, additive): pass


def kind_for(manifest):
    return BaseKind() if manifest["type"] == "base" else FeatureKind()
