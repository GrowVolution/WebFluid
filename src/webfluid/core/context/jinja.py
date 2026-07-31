from webfluid.core.lifecycle.phase import Phase
from webfluid.utils.core import safe_execute


class JinjaContext:
    def __init__(self):
        self._processors = Phase("Context processors")

    def add_processor(self, fn): return self._processors.add(fn)

    async def process(self, ctx):
        for processor in self._processors:
            result = await safe_execute(processor, False)
            if not isinstance(result, dict): continue
            ctx = result | ctx
        return ctx
