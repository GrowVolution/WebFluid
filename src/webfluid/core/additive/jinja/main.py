from jinja2 import PrefixLoader, FileSystemLoader, ChoiceLoader
from frozendict import frozendict

from .rendering import Renderer
from webfluid.core.context.jinja import JinjaContext


class Jinja:
    def __init__(self, additive):
        self.context_dict = {}
        self.context = JinjaContext()
        self.renderer = Renderer(additive, self.context)

        if additive.base:
            self.loader = PrefixLoader({
                additive.id: ChoiceLoader([
                    FileSystemLoader(additive.root_path / "templates"),
                    FileSystemLoader(additive.base.root_path / "templates")
                ])
            })

        elif not additive.is_base:
            self.loader = PrefixLoader({
                additive.id: FileSystemLoader(
                    additive.root_path / "templates"
                )
            })

    def prepare(self, fluid):
        fluid.add_template_loader(self.loader)
        self.context_dict = frozendict(self.context_dict)
