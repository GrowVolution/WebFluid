from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid import Fluid


class BaseContext:
    CTX: ContextVar
    _tokens: list

    def __enter__(self):
        if not hasattr(self, "_tokens"):
            object.__setattr__(self, "_tokens", [])
        self._tokens.append(self.CTX.set(self))
        return self

    def __exit__(self, *args):
        if not hasattr(self, "_tokens") or not self._tokens:
            raise RuntimeError("Context not entered")
        self.CTX.reset(self._tokens.pop())
        if not self._tokens: object.__delattr__(self, "_tokens")

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, *args):
        return self.__exit__(*args)

    @classmethod
    def current(cls):
        try: return cls.CTX.get()
        except LookupError:
            raise RuntimeError(f"No active {cls.__name__}.")


class FluidContext(BaseContext):
    _INTERNAL_KEYS = ("_data", "fluid", "request", "_tokens")
    CTX = ContextVar("fluid.context")

    def __init__(self, fluid: "Fluid", request: FastAPIRequest | FlaskRequest,
                 *args, **kwargs):
        object.__setattr__(self, "fluid", fluid)
        object.__setattr__(self, "request", RawRequest(request))
        object.__setattr__(self, "_data", {})

        self._data.update(kwargs)
        for arg in args:
            name = arg.__name__
            if name in self._data:
                raise ValueError(f"Duplicate argument name: {name}")
            self._data[arg.__name__] = arg

    def __getattr__(self, key):
        try: return self._data[key]
        except KeyError: raise AttributeError(key)

    def __setattr__(self, key, value):
        if key in type(self)._INTERNAL_KEYS or key == "_INTERNAL_KEYS":
            raise AttributeError(key)
        else: self._data[key] = value

    def __delattr__(self, key):
        if key in type(self)._INTERNAL_KEYS or key == "_INTERNAL_KEYS":
            raise AttributeError(key)
        try: del self._data[key]
        except KeyError: raise AttributeError(key)

    def __contains__(self, item): return item in self._data
    def __len__(self): return len(self._data)
    def __iter__(self): return iter(self._data)
    def __dir__(self):
        return list(super().__dir__()) + list(self._data.keys())

    def keys(self): return self._data.keys()
    def values(self): return self._data.values()
    def items(self): return self._data.items()
