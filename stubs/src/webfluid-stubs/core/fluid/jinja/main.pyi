from jinja2 import Environment

from webfluid.core.fluid.jinja.rendering import Renderer as Renderer
from webfluid.core.fluid.jinja.context import Context as Context
from webfluid.core.fluid.jinja.loaders import Loaders as Loaders
from webfluid import Fluid

class Jinja:
    env: Environment
    renderer: Renderer
    context: Context
    loaders: Loaders
    def __init__(self, fluid: Fluid) -> None: ...
    def prepare(self) -> None: ...
