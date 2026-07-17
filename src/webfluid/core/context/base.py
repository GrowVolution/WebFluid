from contextlib import contextmanager
from contextvars import Token


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
