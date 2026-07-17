from jinja2 import Environment

from .rendering import Renderer
from .loaders import Loaders
from webfluid.core.context.jinja import JinjaContext


class Jinja:
    def __init__(self, fluid):
        self.env = Environment(enable_async=True)
        self.context = JinjaContext()
        self.loaders = Loaders(fluid)
        self.renderer = Renderer(self)

    def prepare(self):
        self.loaders.freeze()
        self.env.loader = self.loaders.loader
