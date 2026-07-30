from contextvars import ContextVar

from webfluid.core.context.base import BaseContext


class DomainContext(BaseContext):
    _ctx = ContextVar("babel.domain")
    def __init__(self, domain):
        self.domain = domain


class SelectorContext(BaseContext):
    _ctx = ContextVar("babel.selector")
    def __init__(self, locale_selector, timezone_selector):
        self.locale_selector = locale_selector
        self.timezone_selector = timezone_selector
