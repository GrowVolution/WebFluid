

class Renderer:
    def __init__(self, jinja):
        self.env = jinja.env
        self.context = jinja.context

    async def _render(self, target, ctx):
        return await target.render_async(**await self.context.process(ctx))

    async def render(self, template, **ctx):
        return await self._render(self.env.get_template(template), ctx)

    async def render_string(self, source, **ctx):
        return await self._render(self.env.from_string(source), ctx)
