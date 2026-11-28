from jinja2 import Environment

from webfluid import Fluid
from webfluid.core.context.jinja import JinjaContext
from webfluid.core.fluid.jinja.loaders import Loaders
from webfluid.core.fluid.jinja.rendering import Renderer

_ESCAPED: tuple[str, ...]

def _is_dict(value: object) -> bool: ...

class Jinja:
    env: Environment
    context: JinjaContext
    loaders: Loaders
    renderer: Renderer
    def __init__(self, fluid: Fluid) -> None: ...
    def prepare(self) -> None: ...
