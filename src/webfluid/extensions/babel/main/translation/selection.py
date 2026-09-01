from contextlib import contextmanager, asynccontextmanager

from ..context import SelectorContext


class Selector:
    def __init__(self):
        self._locale_selector_fn = None
        self._timezone_selector_fn = None

    def locale_selector(self, fn):
        self._locale_selector_fn = fn
        return fn

    def timezone_selector(self, fn):
        self._timezone_selector_fn = fn
        return fn

    @property
    def locale_selector_fn(self):
        ctx = SelectorContext.try_current()
        fn = ctx.locale_selector if ctx else None
        return fn if fn is not None else self._locale_selector_fn

    @property
    def timezone_selector_fn(self):
        ctx = SelectorContext.try_current()
        fn = ctx.timezone_selector if ctx else None
        return fn if fn is not None else self._timezone_selector_fn

    @staticmethod
    @contextmanager
    def force(locale=None, timezone=None):
        with SelectorContext(
                (lambda: locale) if locale is not None else None,
                (lambda: timezone) if timezone is not None else None
        ): yield

    @staticmethod
    @asynccontextmanager
    async def aforce(locale=None, timezone=None):
        async with SelectorContext(
                (lambda: locale) if locale is not None else None,
                (lambda: timezone) if timezone is not None else None
        ): yield
