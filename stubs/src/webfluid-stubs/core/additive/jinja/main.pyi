from typing import Any

from frozendict import frozendict
from jinja2 import BaseLoader

from webfluid import Fluid
from webfluid.core.additive.jinja.rendering import Renderer
from webfluid.core.additive.main import Additive
from webfluid.core.context.jinja import JinjaContext

class Jinja:
    context_dict: dict[str, Any] | frozendict[str, Any]
    context: JinjaContext
    renderer: Renderer
    loader: BaseLoader | None
    def __init__(self, additive: Additive, loader: BaseLoader | None) -> None: ...
    def prepare(self, fluid: Fluid) -> None: ...
