from webfluid.utils.core import safe_execute, required_arg_count
from webfluid.utils.logging import factory as log_factory


class HookPhase:
    def __init__(self, name, reverse=False):
        self.name = name

        if self.name not in {"startup", "shutdown"}:
            raise ValueError("Invalid hook phase.")

        self.reverse = reverse
        self._hooks = []
        self._locked = False

    def add_hook(self, fn):
        if self._locked:
            if self.name == "startup":
                raise RuntimeError("Startup hooks cannot be added after the server was started.")
            else:
                raise RuntimeError("Shutdown hooks cannot be added after the server was stopped.")

        if required_arg_count(fn) > 0:
            raise TypeError(f"{self.name.capitalize()} hooks must not receive non optional arguments.")

        self._hooks.append(fn)
        return fn

    async def run_hooks(self):
        self._locked = True
        log_factory.log(f"Running {self.name} hooks...")
        for hook in reversed(self._hooks) if self.reverse else self._hooks:
            await safe_execute(hook, False)


class Lifecycle:
    def __init__(self):
        self.startup = HookPhase("startup")
        self.shutdown = HookPhase("shutdown", reverse=True)

    async def run_startup(self): await self.startup.run_hooks()
    async def run_shutdown(self): await self.shutdown.run_hooks()
