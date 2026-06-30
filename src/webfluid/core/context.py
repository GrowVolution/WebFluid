from contextvars import ContextVar, Token
from contextlib import contextmanager


class BaseContext:
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
    def current(cls):
        try: return cls._ctx.get()
        except LookupError:
            raise RuntimeError(f"No active {cls.__name__}.")

    @classmethod
    @contextmanager
    def outer(cls, depth=1):
        target = cls._ctx.get(None)

        for _ in range(depth):
            tokens = getattr(target, "_tokens", None)
            old = tokens[-1].old_value if tokens else Token.MISSING
            if old is Token.MISSING:
                yield None
                return
            target = old

        token = cls._ctx.set(target)
        try: yield target
        finally: cls._ctx.reset(token)


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
