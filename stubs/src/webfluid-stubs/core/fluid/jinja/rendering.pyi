from typing import Any

from jinja2 import Environment, Template

from webfluid import Fluid
from webfluid.core.context.jinja import JinjaContext
from webfluid.core.fluid.jinja.main import Jinja

INJECT_THEME: str

class Renderer:
    env: Environment
    context: JinjaContext
    fluid: Fluid
    def __init__(self, jinja: Jinja, fluid: Fluid) -> None: ...
    async def _render(self, target: Template, ctx: dict[str, Any]) -> str: ...
    async def render(self, template: str, **ctx: Any) -> str: ...
    async def render_string(self, source: str, **ctx: Any) -> str: ...
