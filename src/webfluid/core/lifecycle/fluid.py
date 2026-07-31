from .phase import Phase
from webfluid.utils.core import safe_execute
from webfluid.utils.cli import progress_bar


class Lifecycle:
    def __init__(self):
        self.startup = Phase(
            "Startup hooks", closed_after="the server was started"
        )
        self.shutdown = Phase(
            "Shutdown hooks", reverse=True,
            closed_after="the server was stopped"
        )

    async def _run(self, phase):
        with progress_bar(f"{phase.name} phase", len(phase)) as bar:
            for hook in phase.seal():
                await safe_execute(hook, False)
                bar.update()

    async def run_startup(self): await self._run(self.startup)
    async def run_shutdown(self): await self._run(self.shutdown)
