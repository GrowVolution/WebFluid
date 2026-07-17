from contextvars import ContextVar

from webfluid.core.context.base import BaseContext


class FluidContext(BaseContext):
    _ctx = ContextVar("fluid.context")
    _ctx_cache = {}

    def __init__(self, fluid, request=None, *args, **kwargs):
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

    @classmethod
    def get_ctx_data(cls, default_config, *requirements):
        data = []

        try:
            ctx = cls.current()
            for req in requirements:
                if req in cls._ctx_cache:
                    d = cls._ctx_cache[req]

                else:
                    d = ctx.fluid.config.get(
                        req, getattr(default_config, req, None)
                    )
                    cls._ctx_cache[req] = d

                data.append(d)

        except RuntimeError:
            from webfluid.utils.logging import factory as log_factory
            log_factory.warning("Running outside a request, using cache or default config.")

            for req in requirements:
                if req in cls._ctx_cache:
                    d = cls._ctx_cache[req]
                else:
                    d = getattr(default_config, req, None)

                data.append(d)

        return data[0] if len(data) == 1 else tuple(data)
