from typing import Any

from jinja2 import PrefixLoader
from frozendict import frozendict

from webfluid import Fluid
from webfluid.core.additive.jinja.rendering import Renderer as Renderer
from webfluid.core.context.jinja import JinjaContext

class Jinja:
    context_dict: dict[str, Any] | frozendict[str, Any]
    context: JinjaContext
    renderer: Renderer
    loader: PrefixLoader
    def __init__(self, additive: Any) -> None: ...
    def prepare(self, fluid: Fluid) -> None: ...
