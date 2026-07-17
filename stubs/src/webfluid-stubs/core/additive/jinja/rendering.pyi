from typing import Any

from webfluid.core.additive.main import Additive
from webfluid.core.context.jinja import JinjaContext

class Renderer:
    additive: Additive
    context: JinjaContext
    def __init__(self, additive: Additive, context: JinjaContext) -> None: ...
    async def render(self, template: str, **ctx: Any) -> str: ...
