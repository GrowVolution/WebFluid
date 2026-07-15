

class Renderer:
    def __init__(self, jinja):
        self.env = jinja.env
        self.context = jinja.context

    async def render(self, template, **ctx):
        is_string = ctx.get("is_string", False)
        target = self.env.from_string(template) \
            if is_string else self.env.get_template(template)
        return await target.render_async(**await self.context.process(ctx))
