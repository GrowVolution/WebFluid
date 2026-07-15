from jinja2 import Environment

from .rendering import Renderer
from .context import Context
from .loaders import Loaders



class Jinja:
    def __init__(self, fluid):
        self.env = Environment(enable_async=True)
        self.context = Context()
        self.loaders = Loaders(fluid)
        self.renderer = Renderer(self)

    def prepare(self):
        self.loaders.freeze()
        self.env.loader = self.loaders.loader
