from jinja2 import Environment

from .rendering import Renderer
from .loaders import Loaders
from webfluid.core.constants import DEBUG
from webfluid.core.context.jinja import JinjaContext


class Jinja:
    def __init__(self, fluid):
        self.env = Environment(
            enable_async=True, auto_reload=DEBUG, cache_size=-1
        )
        self.context = JinjaContext()
        self.loaders = Loaders(fluid)
        self.renderer = Renderer(self)

    def prepare(self):
        self.env.loader = self.loaders.freeze()
