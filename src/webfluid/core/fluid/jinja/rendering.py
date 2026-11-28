from webfluid.core.constants import THEMES

INJECT_THEME = "inject_theme"


class Renderer:
    def __init__(self, jinja, fluid):
        self.env = jinja.env
        self.context = jinja.context
        self.fluid = fluid

    async def _render(self, target, ctx):
        inject = ctx.pop(INJECT_THEME, False) if THEMES else False
        ctx = await self.context.process(ctx)
        if inject: ctx["theme"] = self.fluid.theme_variables()
        return await target.render_async(**ctx)

    async def render(self, template, **ctx):
        return await self._render(self.env.get_template(template), ctx)

    async def render_string(self, source, **ctx):
        return await self._render(self.env.from_string(source), ctx)
