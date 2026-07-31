from jinja2 import ChoiceLoader, PrefixLoader, FileSystemLoader

from webfluid.core.identity import FRAMEWORK_ID, FRAMEWORK_ROOT
from webfluid.core.freeze import Freezable

_template_path = f"{FRAMEWORK_ID}/templates"


class Loaders(Freezable):
    label = "Loaders"
    closed_after = "initialization"

    def __init__(self, fluid):
        super().__init__()
        self._loaders = []
        app_templates = FileSystemLoader(fluid.project_root / _template_path)
        self.add(ChoiceLoader([
            app_templates, PrefixLoader({ "app": app_templates })
        ]))

    def add(self, loader):
        self.guard()
        self._loaders.append(loader)

    def freeze(self, value=None):
        framework_templates = FileSystemLoader(FRAMEWORK_ROOT / _template_path)
        self.add(ChoiceLoader([
            framework_templates, PrefixLoader({ FRAMEWORK_ID: framework_templates })
        ]))
        loaders = tuple(self._loaders)
        del self._loaders
        return super().freeze(ChoiceLoader(loaders))

    @property
    def loader(self): return self.frozen
