from typing import Any

from jinja2 import Environment

from webfluid.core.fluid.jinja import Jinja
from webfluid.core.context.jinja import JinjaContext

class Renderer:
    env: Environment
    context: JinjaContext
    def __init__(self, jinja: Jinja) -> None: ...
    async def render(self, template: str, **ctx: Any) -> str: ...
