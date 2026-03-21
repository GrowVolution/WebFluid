from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request
    from webfluid import Fluid


class BaseContext:
    _ctx: ContextVar
    _tokens: list

    def __enter__(self):
        if not hasattr(self, "_tokens"):
            self._tokens = []
        self._tokens.append(self._ctx.set(self))
        return self

    def __exit__(self, *args):
        if not hasattr(self, "_tokens") or not self._tokens:
            raise RuntimeError("Context not entered")
        self._ctx.reset(self._tokens.pop())
        if not self._tokens: del self._tokens
        return False

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, *args):
        return self.__exit__(*args)

    @classmethod
    def current(cls) -> "BaseContext":
        try: return cls._ctx.get()
        except LookupError:
            raise RuntimeError(f"No active {cls.__name__}.")


class FluidContext(BaseContext):
    _ctx = ContextVar("fluid.context")

    def __init__(self, fluid: "Fluid", request: "Request",
                 *args, **kwargs):
        self.fluid = fluid
        self.request = request
        self._data = {}

        self._data.update(kwargs)
        for arg in args:
            name = arg.__name__
            if name in self._data:
                raise ValueError(f"Duplicate argument name: {name}")
            self._data[arg.__name__] = arg

    def __getitem__(self, key): return self._data[key]
    def __setitem__(self, key, value): self._data[key] = value
    def __contains__(self, item): return item in self._data
    def __len__(self): return len(self._data)
    def __str__(self): return str(self._data)

    def keys(self): return self._data.keys()
    def values(self): return self._data.values()
    def items(self): return self._data.items()
    def get(self, key, default=None): return self._data.get(key, default)
    def pop(self, key, default=None): return self._data.pop(key, default)
