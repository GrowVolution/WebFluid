from webfluid.utils.core import safe_execute, required_arg_count


class HookPhase:
    def __init__(self, stage, reverse=False):
        self.before = stage == "before_enable"
        self.after = stage == "after_enable"

        if not (self.before or self.after):
            raise ValueError("Invalid hook phase.")

        self.reverse = reverse
        self._hooks = []
        self._locked = False

    def add_hook(self, fn):
        if self._locked:
            raise RuntimeError("Enable hooks cannot be added after the additive was enabled.")

        if required_arg_count(fn) != 1 and self.before:
            raise TypeError(
                "Enable hooks (before) must receive exactly one non optional argument (type Fluid)."
            )
        elif required_arg_count(fn) > 0 and self.after:
            raise TypeError("Enable hooks (after) must not receive non optional arguments.")

        self._hooks.append(fn)
        return fn

    async def run_hooks(self, *args):
        self._locked = True
        for hook in reversed(self._hooks) if self.reverse else self._hooks:
            await safe_execute(hook, False, *args)


class Lifecycle:
    def __init__(self):
        self.before_enable = HookPhase("before_enable")
        self.after_enable = HookPhase("after_enable", reverse=True)

    async def run_before(self, fluid): await self.before_enable.run_hooks(fluid)
    async def run_after(self): await self.after_enable.run_hooks()
