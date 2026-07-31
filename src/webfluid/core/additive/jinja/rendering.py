from webfluid.core.context.fluid import FluidContext


class Renderer:
    def __init__(self, additive, context):
        self.additive = additive
        self.context = context

    async def render(self, template, **ctx):
        ctx = await self.context.process(ctx)

        if self.additive.parent:
            return await self.additive.parent.render(template, **ctx)

        return await FluidContext.current().fluid.render(
            f"{self.additive.id}/{template}", **ctx
        )
