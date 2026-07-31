from contextvars import ContextVar

from webfluid.core.context.base import BaseContext


class FluidContext(BaseContext):
    _ctx = ContextVar("fluid.context")

    def __init__(self, fluid, request=None, *args, **kwargs):
        self.fluid = fluid
        self.request = request
        self._data = {}
        self._cache = {}

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

    def cached(self, key, factory):
        if key not in self._cache:
            self._cache[key] = factory()
        return self._cache[key]

    @classmethod
    def cached_or(cls, key, factory):
        ctx = cls.try_current()
        if ctx is None: return factory()
        return ctx.cached(key, factory)
