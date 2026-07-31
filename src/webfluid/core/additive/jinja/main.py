from frozendict import frozendict

from .rendering import Renderer
from webfluid.core.context.jinja import JinjaContext


class Jinja:
    def __init__(self, additive, loader):
        self.context_dict = {}
        self.context = JinjaContext()
        self.renderer = Renderer(additive, self.context)
        self.loader = loader

    def prepare(self, fluid):
        if self.loader is not None:
            fluid.add_template_loader(self.loader)
        self.context_dict = frozendict(self.context_dict)
