from jinja2 import ChoiceLoader, PrefixLoader, FileSystemLoader

from webfluid.core.constants import FRAMEWORK_ID, FRAMEWORK_ROOT

_template_path = f"{FRAMEWORK_ID}/templates"


class Loaders:
    def __init__(self, fluid):
        self._loaders = []
        self._frozen = None
        app_templates = FileSystemLoader(fluid.project_root / _template_path)
        self.add(ChoiceLoader([
            app_templates, PrefixLoader({ "app": app_templates })
        ]))

    def add(self, loader):
        if self._frozen is not None:
            raise RuntimeError("Loaders cannot be added after initialization.")
        self._loaders.append(loader)

    def freeze(self):
        framework_templates = FileSystemLoader(FRAMEWORK_ROOT / _template_path)
        self.add(ChoiceLoader([
            framework_templates, PrefixLoader({ FRAMEWORK_ID: framework_templates })
        ]))
        self._frozen = tuple(self._loaders)
        del self._loaders

    @property
    def loader(self):
        if self._frozen is None:
            raise RuntimeError("Loaders must be frozen before use.")
        return ChoiceLoader(self._frozen)
