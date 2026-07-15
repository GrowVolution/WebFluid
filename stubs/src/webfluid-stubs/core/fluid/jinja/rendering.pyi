from typing import Any

from jinja2 import Environment

from webfluid.core.fluid.jinja import Jinja
from webfluid.core.fluid.jinja.context import Context

class Renderer:
    env: Environment
    context: Context
    def __init__(self, jinja: Jinja) -> None: ...
    async def render(self, template: str, **ctx: Any) -> str: ...
