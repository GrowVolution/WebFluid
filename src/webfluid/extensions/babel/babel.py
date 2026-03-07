from contextvars import ContextVar
from contextlib import contextmanager, asynccontextmanager
from babel import Locale
from pathlib import Path
from typing import TYPE_CHECKING, Callable
import sys, subprocess

from webfluid.core.context import BaseContext
from webfluid.extensions.babel.constants import (
    DEFAULT_DATE_FORMATS,
    DEFAULT_LOCALE,
    DEFAULT_TIMEZONE,
    DateFormat,
    DateFormatKey
)
from webfluid.extensions.utils.babel import (
    format_currency,
    format_date,
    format_datetime,
    format_decimal,
    format_number,
    format_percent,
    format_scientific,
    format_time,
    format_timedelta
)
from webfluid.utils import is_async_function
from webfluid.exceptions import FrameworkException


if TYPE_CHECKING:
    from webfluid import Fluid
    from webfluid.extensions.babel.domain import Domain


class _DomainContext(BaseContext):
    CTX = ContextVar("babel.domain")
    def __init__(self, domain: "Domain"):
        self.domain = domain


class SelectorContext(BaseContext):
    CTX = ContextVar("babel.selector")
    def __init__(self, locale_selector: Callable, timezone_selector: Callable):
        self.locale_selector = locale_selector
        self.timezone_selector = timezone_selector


class Babel:
    def __init__(self, fluid: "Fluid | None" = None,
                 default_locale: str = DEFAULT_LOCALE,
                 default_timezone: str = DEFAULT_TIMEZONE,
                 date_formats: dict[DateFormatKey, DateFormat] | None = None,
                 configure_jinja: bool = True,
                 default_domain: "Domain | None" = None):
        self.default_domain = None
        self.default_locale = None
        self.default_timezone = None
        self.supported_locales = None
        self._locale_cache = {}
        self._domains = {}

        self._locale_selector_fn = None
        self._timezone_selector_fn = None
        self.date_formats = None

        self.initialized = False

        if fluid is not None:
            self.init_fluid(fluid, default_locale,
                            default_timezone, date_formats,
                            configure_jinja, default_domain)

    def init_fluid(self, fluid: "Fluid",
                   default_locale: str = DEFAULT_LOCALE,
                   default_timezone: str = DEFAULT_TIMEZONE,
                   date_formats: dict[DateFormatKey, DateFormat] | None = None,
                   configure_jinja: bool = True,
                   default_domain: "Domain | None" = None):
        if self.initialized: raise FrameworkException("Extension has already been initialized.")

        if default_domain is None:
            from webfluid.extensions.babel.domain import Domain
            default_domain = Domain()
        self.default_domain = default_domain
        self.default_locale = fluid.config.get("BABEL_DEFAULT_LOCALE", default_locale)
        self.default_timezone = fluid.config.get("BABEL_DEFAULT_TIMEZONE", default_timezone)
        supported_locales = fluid.config.get("BABEL_SUPPORTED_LOCALES", [default_locale])
        self.supported_locales = tuple(supported_locales)
        self.date_formats = date_formats or DEFAULT_DATE_FORMATS.copy()

        db_bind = fluid.config.get("BABEL_DATABASE_BIND")
        if db_bind is not None:
            from webfluid.extensions.babel.translations import I18nMessage
            I18nMessage.set_bind(db_bind)

        if configure_jinja:
            fluid.jinja_env.filters.update(
                datetimeformat=format_datetime,
                dateformat=format_date,
                timeformat=format_time,
                timedeltaformat=format_timedelta,
                numberformat=format_number,
                decimalformat=format_decimal,
                currencyformat=format_currency,
                percentformat=format_percent,
                scientificformat=format_scientific,
            )
            fluid.jinja_env.add_extension("jinja2.ext.i18n")
            fluid.jinja_env.install_gettext_callables(
                lambda x: get_domain().get_translations().ugettext(x),
                lambda s, p, n: get_domain().get_translations().ungettext(s, p, n),
                newstyle=True,
            )

        self.initialized = True

    def register_additive(self): pass

    def locale_selector(self, fn: Callable) -> Callable:
        self._locale_selector_fn = fn
        return fn

    def timezone_selector(self, fn: Callable) -> Callable:
        self._timezone_selector_fn = fn
        return fn

    def load_locale(self, locale: str) -> Locale:
        cached = self._locale_cache.get(locale)
        if cached: return cached
        if "-" in locale: locale = locale.replace("-", "_")
        parsed = Locale.parse(locale)
        self._locale_cache[locale] = parsed
        return parsed

    def domain_context(self, domain: str):
        def decorator(fn):
            if is_async_function(fn):
                async def wrapper(*args, **kwargs):
                    async with _DomainContext(
                        self._domains.get(domain, self.default_domain)
                    ): return await fn(*args, **kwargs)
            else:
                def wrapper(*args, **kwargs):
                    with _DomainContext(
                        self._domains.get(domain, self.default_domain)
                    ): return fn(*args, **kwargs)
            return wrapper
        return decorator

    def extract_fallback(self):
        pot = "messages.pot"
        trans = Path(self.current_domain.get_translations_path(None))
        babel_cli = "babel.messages.frontend"
        has_catalogs = any(translations.glob("*/LC_MESSAGES/*.po"))

        subprocess.run(
            [sys.executable, "-m", babel_cli, "extract",
            "-F", str(Path(__file__).parent / "babel.cfg"),
            "-o", pot,
            os.getcwd()],
            check=True
        )

        if has_catalogs:
            subprocess.run(
                [sys.executable, "-m", babel_cli, "update",
                "-i", pot,
                "-d", trans],
                check=True
            )

        else:
            subprocess.run(
                [sys.executable, "-m", babel_cli, "init",
                "-i", pot,
                "-d", trans,
                "-l", "en"],
                check=True
            )

        subprocess.run(
            [sys.executable, "-m", babel_cli, "compile",
            "-d", trans],
            check=True
        )

    @property
    def current_domain(self) -> "Domain":
        try: return _DomainContext.current().domain
        except RuntimeError: return self.default_domain

    @property
    def locale_selector_fn(self) -> Callable:
        try:
            fn = SelectorContext.current().locale_selector
            if fn is None: return self._locale_selector_fn
            return fn
        except RuntimeError: return self._locale_selector_fn

    @property
    def timezone_selector_fn(self) -> Callable:
        try:
            fn = SelectorContext.current().timezone_selector
            if fn is None: return self._timezone_selector_fn
            return fn
        except RuntimeError: return self._timezone_selector_fn

    @staticmethod
    @contextmanager
    def force(locale: str = None, timezone: str = None):
        with SelectorContext(
                (lambda: locale) if locale is not None else None,
                (lambda: timezone) if timezone is not None else None
        ): yield

    @staticmethod
    @asynccontextmanager
    async def aforce(locale: str = None, timezone: str = None):
        async with SelectorContext(
                (lambda: locale) if locale is not None else None,
                (lambda: timezone) if timezone is not None else None
        ): yield
