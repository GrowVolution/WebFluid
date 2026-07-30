from .translation import Translator
from .socket import Socket
from .cli import CLIExtension

from webfluid.extensions.base import FluidExtension
from webfluid.extensions.babel.constants import (
    DEFAULT_DATE_FORMATS,
    DEFAULT_LOCALE,
    DEFAULT_TIMEZONE
)
from webfluid.extensions.babel.utils import (
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
from webfluid.core.constants import (
    WF_STATIC, EXECUTION,
    EXT_SQLALCHEMY
)
from webfluid.exceptions import FrameworkException


class Babel(FluidExtension):
    _cli = CLIExtension.cli
    
    def __init__(self, fluid=None, default_domain=None):
        self.default_locale = None
        self.default_timezone = None
        self.supported_locales = None
        self.date_formats = None
        self._translator = None
        self._socket = None

        super().__init__(fluid, default_domain=default_domain)

    def expand_fluid(self, fluid, *_, **kwargs):
        if not EXT_SQLALCHEMY:
            raise FrameworkException("EXT_SQLALCHEMY is required for Babel to work.")

        self.default_locale = fluid.config.get("BABEL_DEFAULT_LOCALE", DEFAULT_LOCALE)
        self.default_timezone = fluid.config.get("BABEL_DEFAULT_TIMEZONE", DEFAULT_TIMEZONE)
        supported_locales = fluid.config.get("BABEL_SUPPORTED_LOCALES", [DEFAULT_LOCALE])
        self.supported_locales = tuple(supported_locales)
        self.date_formats = fluid.config.get("BABEL_DATE_FORMATS", DEFAULT_DATE_FORMATS.copy())
        
        self._translator = Translator(kwargs.get("default_domain"), fluid.config.get(
            "BABEL_DISABLE_AUTOUPDATE", False
        ))
        self._socket = Socket(self)

        db_bind = fluid.config.get("BABEL_DATABASE_BIND")
        if db_bind is not None:
            from ..translations import I18nKey, I18nMessage
            I18nKey.set_bind(db_bind)
            I18nMessage.set_bind(db_bind)

        elif not EXECUTION:
            # Initialize models to ensure they are registered in the metadata
            from ..translations import I18nKey, I18nMessage

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
            fluid.websocket("/ws/i18n")(self._socket.endpoint)
            fluid.add_source(
                f'<script src="{WF_STATIC}/js/i18n.js" type="module"></script>',
                priority=5
            )

        fluid.startup_hook(lambda: self._translator.translations.startup_hook(
            self, self._translator.domains
        ))
        
    def _ensure_initialized(self):
        if not self._translator:
            raise FrameworkException("Babel.expand_fluid() has not been called.")
        
    @property
    def gettext(self):
        self._ensure_initialized()
        return self._translator.gettext
    
    @property
    def ngettext(self):
        self._ensure_initialized()
        return self._translator.ngettext
    
    @property
    def pgettext(self):
        self._ensure_initialized()
        return self._translator.pgettext
    
    @property
    def npgettext(self):
        self._ensure_initialized()
        return self._translator.npgettext
    
    @property
    def lazy_gettext(self):
        self._ensure_initialized()
        return self._translator.lazy_gettext
    
    @property
    def lazy_ngettext(self):
        self._ensure_initialized()
        return self._translator.lazy_ngettext
    
    @property
    def lazy_pgettext(self):
        self._ensure_initialized()
        return self._translator.lazy_pgettext
    
    @property
    def lazy_npgettext(self):
        self._ensure_initialized()
        return self._translator.lazy_npgettext
    
    @property
    def register_domain(self):
        self._ensure_initialized()
        return self._translator.domains.register_domain
    
    @property
    def domain_context(self):
        self._ensure_initialized()
        return self._translator.domains.domain_context
    
    @property
    def current_domain(self):
        self._ensure_initialized()
        return self._translator.domains.current_domain
    
    @property
    def update_translations(self):
        self._ensure_initialized()
        return self._translator.translations.update_translations
    
    @property
    def locale_selector(self):
        self._ensure_initialized()
        return self._translator.selector.locale_selector

    @property
    def timezone_selector(self):
        self._ensure_initialized()
        return self._translator.selector.timezone_selector

    @property
    def locale_selector_fn(self):
        self._ensure_initialized()
        return self._translator.selector.locale_selector_fn

    @property
    def timezone_selector_fn(self):
        self._ensure_initialized()
        return self._translator.selector.timezone_selector_fn

    @property
    def force(self):
        self._ensure_initialized()
        return self._translator.selector.force

    @property
    def aforce(self):
        self._ensure_initialized()
        return self._translator.selector.aforce
