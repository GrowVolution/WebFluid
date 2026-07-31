from .phase import Phase
from webfluid.utils.core import safe_execute


class Lifecycle:
    def __init__(self):
        self.before = Phase("Before request processors")
        self.after = Phase(
            "After request processors", arity=1,
            argument="response", reverse=True
        )

    async def process_before(self):
        for processor in self.before:
            response = await safe_execute(processor, True)
            if response is not None: return response
        return None

    async def process_after(self, response):
        for processor in self.after:
            response = await safe_execute(processor, True, response)
        return response
