from webfluid.utils.core import required_arg_count, safe_execute


class Context:
    def __init__(self):
        self._processors = []

    def add_processor(self, fn):
        if required_arg_count(fn) > 0:
            raise TypeError("Context processors must not receive non optional arguments.")
        self._processors.append(fn)
        return fn

    async def process(self, ctx):
        for processor in self._processors:
            result = await safe_execute(processor, False)
            if not isinstance(result, dict): continue
            ctx = result | ctx
        return ctx
