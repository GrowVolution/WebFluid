from jinja2 import Environment

from webfluid.core.fluid.jinja.rendering import Renderer as Renderer
from webfluid.core.context.jinja import JinjaContext as JinjaContext
from webfluid.core.fluid.jinja.loaders import Loaders as Loaders
from webfluid import Fluid

class Jinja:
    env: Environment
    renderer: Renderer
    context: JinjaContext
    loaders: Loaders
    def __init__(self, fluid: Fluid) -> None: ...
    def prepare(self) -> None: ...
