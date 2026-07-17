from webfluid.core.context.fluid import FluidContext


class Renderer:
    def __init__(self, additive, context):
        self.additive = additive
        self.context = context

    async def render(self, template, **ctx):
        ctx = await self.context.process(ctx)
        ctx.pop("is_string", None)

        if self.additive.parent:
            return await self.additive.parent.render(template, **ctx)

        c = FluidContext.current()
        return await c.fluid.render(f"{self.additive.id}/{template}", **ctx)
