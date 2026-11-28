from jinja2 import Environment, select_autoescape

from .contrast import contrast, is_light
from .loaders import Loaders
from .rendering import Renderer
from webfluid.core.constants import DEBUG
from webfluid.core.context.jinja import JinjaContext

_ESCAPED = ("html", "htm", "xml", "xhtml", "svg")


def _is_dict(value):
    return isinstance(value, dict)


class Jinja:
    def __init__(self, fluid):
        self.env = Environment(
            enable_async=True,
            auto_reload=DEBUG,
            autoescape=select_autoescape(_ESCAPED),
            cache_size=-1
        )
        self.env.tests["dict"] = _is_dict
        self.env.tests["light"] = is_light
        self.env.filters["contrast"] = contrast
        self.context = JinjaContext()
        self.loaders = Loaders(fluid)
        self.renderer = Renderer(self, fluid)

    def prepare(self):
        self.env.loader = self.loaders.freeze()
