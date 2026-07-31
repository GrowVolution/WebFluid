from .phase import Phase
from webfluid.utils.core import safe_execute
from webfluid.utils.cli import progress_bar
from webfluid.utils.logging import factory as log_factory


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
        log_factory.log(f"Running {phase.name.lower()}...")
        with progress_bar(f"{phase.name} phase", len(phase), leave=False) as bar:
            for hook in phase.seal():
                await safe_execute(hook, False)
                bar.update()

    async def run_startup(self): await self._run(self.startup)
    async def run_shutdown(self): await self._run(self.shutdown)
