from fastapi import WebSocket
from contextvars import ContextVar
from contextlib import contextmanager, asynccontextmanager
from babel import Locale
from pathlib import Path
from functools import wraps
from typing import TYPE_CHECKING, Callable, Any, Optional
import sys, subprocess, typer, json

from webfluid.extensions.base import FluidExtension
from webfluid.extensions.babel.constants import (
    DEFAULT_DATE_FORMATS,
    DEFAULT_LOCALE,
    DEFAULT_TIMEZONE
)
from webfluid.extensions.babel.speaklater import LazyString
from webfluid.extensions.babel.utils import (
    parse_best_match,
    load_locale,
    format_message,
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
from webfluid.core.context import BaseContext
from webfluid.core.constants import (
    FRAMEWORK_ROOT, FRAMEWORK_ID,
    WF_STATIC, EXECUTION,
    EXT_SQLALCHEMY
)
from webfluid.utils.core import is_async_function
from webfluid.exceptions import FrameworkException


if TYPE_CHECKING:
    from zoneinfo import ZoneInfo
    from webfluid import Fluid
    from webfluid.extensions.babel import Domain


class _DomainContext(BaseContext):
    _ctx = ContextVar("babel.domain")
    def __init__(self, domain: "Domain"):
        self.domain = domain


class SelectorContext(BaseContext):
    _ctx = ContextVar("babel.selector")
    def __init__(self,
                 locale_selector: Optional[Callable],
                 timezone_selector: Optional[Callable]):
        self.locale_selector = locale_selector
        self.timezone_selector = timezone_selector


class Babel(FluidExtension):
    _cli = typer.Typer(help="WebFluid Babel CLI")
    _api_whitelist = {
        "gettext", "ngettext",
        "pgettext", "npgettext"
    }

    def __init__(self, fluid: Optional["Fluid"] = None,
                 default_domain: Optional["Domain"] = None):
        self.default_domain = None
        self.default_locale = None
        self.default_timezone = None
        self.supported_locales = None
        self._domains = {}
        self._update_tasks = []
        self._update_disabled = False
        self._update_blocked = False

        self._locale_selector_fn = None
        self._timezone_selector_fn = None
        self.date_formats = None

        super().__init__(fluid, default_domain=default_domain)

    def expand_fluid(self, fluid: "Fluid", *_,
                     default_domain: Optional["Domain"] = None):
        if not EXT_SQLALCHEMY:
            raise FrameworkException("EXT_SQLALCHEMY is required for Babel to work.")

        if default_domain is None:
            from .domain import Domain
            default_domain = Domain()
        self.default_domain = default_domain
        self.default_locale = fluid.config.get("BABEL_DEFAULT_LOCALE", DEFAULT_LOCALE)
        self.default_timezone = fluid.config.get("BABEL_DEFAULT_TIMEZONE", DEFAULT_TIMEZONE)
        supported_locales = fluid.config.get("BABEL_SUPPORTED_LOCALES", [DEFAULT_LOCALE])
        self.supported_locales = tuple(supported_locales)
        self.date_formats = fluid.config.get("BABEL_DATE_FORMATS", DEFAULT_DATE_FORMATS.copy())

        db_bind = fluid.config.get("BABEL_DATABASE_BIND")
        if db_bind is not None:
            from .translations import I18nKey, I18nMessage
            I18nKey.set_bind(db_bind)
            I18nMessage.set_bind(db_bind)

        elif not EXECUTION:
            # Initialize models to ensure they are registered in the metadata
            from .translations import I18nKey, I18nMessage

        if fluid.config.get("BABEL_CONFIGURE_JINJA", True):
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
                lambda x: self.gettext(x),
                lambda s, p, n: self.ngettext(s, p, n),
                newstyle=True,
            )

        if fluid.config.get("BABEL_CONFIGURE_SOCKET", True):
            fluid.websocket("/ws/i18n")(self.socket_i18n)
            fluid.add_source(
                f'<script src="{WF_STATIC}/js/i18n.js" type="module"></script>',
                priority=5
            )

        self._update_disabled = fluid.config.get("BABEL_DISABLE_AUTOUPDATE", False)
        async def hook():
            if not self._update_disabled: await self._update_translations()
            await self.load_translations()

        fluid.startup_hook(hook)

    def register_domain(self, name: str, package: Path | None = None):
        if name in self._domains:
            raise FrameworkException(f"Domain '{name}' already registered.")

        from .domain import Domain
        self._domains[name] = Domain(
            (package / "translations") if package else None,
            domain=name
        )

    async def load_translations(self):
        domains = [self.default_domain.domain]
        for domain in self._domains.values():
            domains.append(domain.domain)

        tasks = []

        from .translations import MergedTranslations
        for domain in domains:
            for locale in self.supported_locales:
                tasks.append(
                    MergedTranslations.db_load(locale, domain)
                )

        for task in tasks: await task

    def update_translations(self, domain: str,
                            translations: Callable[[], dict[
                                str, dict[
                                    str, dict[
                                        tuple[str, str | None], str
                                    ]
                                ]
                            ]]):
        if self._update_disabled: return

        if self._update_blocked:
            raise FrameworkException("Translation updates are not allowed after startup.")

        from .translations import MergedTranslations
        self._update_tasks.append(
            MergedTranslations.update(domain, translations)
        )

    async def _update_translations(self):
        self._update_blocked = True
        if not self._update_tasks: return
        for task in self._update_tasks: await task
        del self._update_tasks

    async def socket_i18n(self, ws: WebSocket):
        await ws.accept()

        from .translations import MergedTranslations
        while True:
            try:
                msg = json.loads(await ws.receive_text())
            except json.JSONDecodeError:
                await ws.send_text(json.dumps({"error": "invalid json"}))
                continue

            for key in {"id", "type", "data"}:
                if key not in msg:
                    await ws.send_text(json.dumps({"error": f"missing '{key}' in message"}))
                    break
            else:
                response = {
                    "id": msg["id"]
                }

                request = msg["type"]
                if request == "cache":
                    locale = str(load_locale(
                        msg["data"].get("locale")
                        or ws.cookies.get("lang")
                        or parse_best_match(
                            ws.headers.get("Accept-Language", "en-US"),
                            self.supported_locales
                        )
                        or self.default_locale
                    ))

                    cache = MergedTranslations.cache(locale)
                    if cache:
                        response["data"] = {
                            "locale": locale,
                            "translations": cache
                        }
                    else:
                        response["error"] = "Cache not found."

                elif request == "translate":
                    fn_name = msg["data"].get("fn", "gettext")
                    if fn_name not in Babel._api_whitelist:
                        response["error"] = "Only (non lazy) gettext api is supported."

                    else:
                        domain = msg["data"].get("domain")
                        fn = getattr(self, fn_name)
                        if domain: fn = self.domain_context(domain)(fn)
                        response["data"] = fn(
                            *msg["data"]["args"],
                            **msg["data"]["variables"]
                        )

                else:
                    response["error"] = f"Unknown request: {request}"

                await ws.send_text(json.dumps(response))

    def locale_selector(self, fn: Callable) -> Callable:
        self._locale_selector_fn = fn
        return fn

    def timezone_selector(self, fn: Callable) -> Callable:
        self._timezone_selector_fn = fn
        return fn

    def domain_context(self, domain: str) -> Callable:
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
            return wraps(fn)(wrapper)
        return decorator

    def gettext(self, string: str, **variables: Any) -> str:
        for domain in self._fallback_escalation:
            t = domain.get_translations()

            msg = t.gettext(string)
            if msg != string:
                return format_message(msg, **variables)

        return format_message(string, **variables)

    def ngettext(self, singular: str, plural: str, num: int, **variables: Any):
        variables.setdefault("num", num)

        for domain in self._fallback_escalation:
            t = domain.get_translations()

            msg = t.ngettext(singular, plural, num)
            if msg not in (singular, plural):
                return format_message(msg, **variables)

        return format_message(singular if num == 1 else plural, **variables)

    def pgettext(self, context: str, string: str, **variables: Any):
        for domain in self._fallback_escalation:
            t = domain.get_translations()

            msg = t.pgettext(context, string)
            if msg != string:
                return format_message(msg, **variables)

        return self.gettext(string, **variables)

    def npgettext(
            self, context: str, singular: str, plural: str, num: int,
            **variables: Any
    ):
        variables.setdefault("num", num)

        for domain in self._fallback_escalation:
            t = domain.get_translations()

            msg = t.npgettext(context, singular, plural, num)
            if msg not in (singular, plural):
                return format_message(msg, **variables)

        return self.ngettext(singular, plural, num, **variables)

    def lazy_gettext(self, string: str, **variables: Any):
        return LazyString(self.gettext, string, **variables)

    def lazy_ngettext(self, singular: str, plural: str, num: int, **variables: Any):
        return LazyString(self.ngettext, singular, plural, num, **variables)

    def lazy_pgettext(self, context: str, string: str, **variables: Any):
        return LazyString(self.pgettext, context, string, **variables)

    def lazy_npgettext(self, context: str, singular: str, plural: str, num: int, **variables: Any):
        return LazyString(self.npgettext, context, singular, plural, num, **variables)

    @property
    def _fallback_escalation(self) -> list["Domain"]:
        current = self.current_domain
        domains = [current]

        if domains[0] != self.default_domain:
            domains.append(self.default_domain)

        if "__fallback__" in self._domains:
            domains.append(self._domains["__fallback__"])

        if FRAMEWORK_ID in self._domains:
            domains.append(self._domains[FRAMEWORK_ID])

        return domains

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
    def force(
            locale: Optional[str | Locale] = None,
            timezone: Optional["str | ZoneInfo"] = None
    ):
        with SelectorContext(
                (lambda: locale) if locale is not None else None,
                (lambda: timezone) if timezone is not None else None
        ): yield

    @staticmethod
    @asynccontextmanager
    async def aforce(
            locale: Optional[str | Locale] = None,
            timezone: Optional["str | ZoneInfo"] = None
    ):
        async with SelectorContext(
                (lambda: locale) if locale is not None else None,
                (lambda: timezone) if timezone is not None else None
        ): yield

    @staticmethod
    def extract_fallback(project_root: Path):
        pot = "messages.pot"
        trans = project_root / "translations"
        babel_cli = "babel.messages.frontend"
        has_catalogs = any(trans.glob("*/LC_MESSAGES/*.po"))

        subprocess.run(
            [sys.executable, "-m", babel_cli, "extract",
             "-F", str(Path(__file__).parent / "babel.cfg"),
             "-o", pot,
             str(project_root), str(FRAMEWORK_ROOT)],
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

    @staticmethod
    @_cli.command()
    def extract(): Babel.extract_fallback(Path.cwd())
