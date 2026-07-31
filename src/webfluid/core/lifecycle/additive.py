from .phase import Phase
from webfluid.utils.core import safe_execute


class Lifecycle:
    def __init__(self):
        self.before_enable = Phase(
            "Enable hooks (before)", arity=1, argument="fluid",
            closed_after="the additive was enabled"
        )
        self.after_enable = Phase(
            "Enable hooks (after)", reverse=True,
            closed_after="the additive was enabled"
        )

    async def _run(self, phase, *args):
        for hook in phase.seal():
            await safe_execute(hook, False, *args)

    async def run_before(self, fluid): await self._run(self.before_enable, fluid)
    async def run_after(self): await self._run(self.after_enable)
