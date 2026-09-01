from functools import wraps
from inspect import iscoroutinefunction

from ..context import DomainContext
from webfluid.utils.core import async_result
from webfluid.exceptions import FrameworkException


class Domains:
    def __init__(self, default_domain):
        self.store = {}

        if default_domain is None:
            from webfluid.extensions.babel.domain import Domain
            default_domain = Domain()
        self.default_domain = default_domain

    def register_domain(self, name, package=None):
        if name in self.store:
            raise FrameworkException(f"Domain '{name}' already registered.")

        from webfluid.extensions.babel.domain import Domain
        self.store[name] = Domain(
            (package / "translations") if package else None,
            domain=name
        )

    def domain_context(self, domain):
        def decorator(fn):
            if iscoroutinefunction(fn):
                async def wrapper(*args, **kwargs):
                    with DomainContext(
                            self.store.get(domain, self.default_domain)
                    ): return await async_result(fn(*args, **kwargs))
            else:
                def wrapper(*args, **kwargs):
                    with DomainContext(
                            self.store.get(domain, self.default_domain)
                    ): return fn(*args, **kwargs)
            return wraps(fn)(wrapper)
        return decorator

    @property
    def current_domain(self):
        ctx = DomainContext.try_current()
        return ctx.domain if ctx else self.default_domain
