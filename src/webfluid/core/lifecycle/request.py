from webfluid.utils.core import required_arg_count, safe_execute


class RequestPhase:
    def __init__(self, stage, reverse=False):
        self.before = stage == "before"
        self.after = stage == "after"

        if not (self.before or self.after):
            raise ValueError("Invalid request phase.")

        self.reverse = reverse
        self._processors = []

    def add_processor(self, fn):
        if required_arg_count(fn) > 0 and self.before:
            raise TypeError("Before request processors must not receive non optional arguments.")
        elif required_arg_count(fn) != 1 and self.after:
            raise TypeError("After request processors must receive exactly one argument (response).")

        self._processors.append(fn)
        return fn

    async def _process_before(self):
        for processor in reversed(self._processors) if self.reverse else self._processors:
            response = await safe_execute(processor, True)
            if response is not None: return response
        return None

    async def _process_after(self, response):
        for processor in reversed(self._processors) if self.reverse else self._processors:
            response = await safe_execute(processor, True, response)
        return response

    async def process(self, response=None):
        if self.before: return await self._process_before()
        elif self.after: return await self._process_after(response)
        return None


class Lifecycle:
    def __init__(self):
        self.before = RequestPhase("before")
        self.after = RequestPhase("after", reverse=True)

    async def process_before(self):
        return await self.before.process()

    async def process_after(self, response):
        return await self.after.process(response)
