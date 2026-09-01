from .translation import Translator
from .socket import Socket
from .cli import CLIExtension

from webfluid.extensions.base import Delegated, FluidExtension
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
    FRAMEWORK_STATIC, EXECUTION,
    EXT_SQLALCHEMY
)
from webfluid.exceptions import FrameworkException


class Babel(FluidExtension):
    _cli = CLIExtension.cli

    gettext = Delegated("_translator.gettext")
    ngettext = Delegated("_translator.ngettext")
    pgettext = Delegated("_translator.pgettext")
    npgettext = Delegated("_translator.npgettext")

    agettext = Delegated("_translator.agettext")
    angettext = Delegated("_translator.angettext")
    apgettext = Delegated("_translator.apgettext")
    anpgettext = Delegated("_translator.anpgettext")

    lazy_gettext = Delegated("_translator.lazy_gettext")
    lazy_ngettext = Delegated("_translator.lazy_ngettext")
    lazy_pgettext = Delegated("_translator.lazy_pgettext")
    lazy_npgettext = Delegated("_translator.lazy_npgettext")

    register_domain = Delegated("_translator.domains.register_domain")
    domain_context = Delegated("_translator.domains.domain_context")
    current_domain = Delegated("_translator.domains.current_domain")
    update_translations = Delegated("_translator.translations.update_translations")

    locale_selector = Delegated("_translator.selector.locale_selector")
    timezone_selector = Delegated("_translator.selector.timezone_selector")
    locale_selector_fn = Delegated("_translator.selector.locale_selector_fn", True)
    timezone_selector_fn = Delegated("_translator.selector.timezone_selector_fn", True)
    force = Delegated("_translator.selector.force")
    aforce = Delegated("_translator.selector.aforce")

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

        config = fluid.config
        self.default_locale = config["BABEL_DEFAULT_LOCALE"]
        self.default_timezone = config["BABEL_DEFAULT_TIMEZONE"]
        self.supported_locales = tuple(config["BABEL_SUPPORTED_LOCALES"])
        self.date_formats = config["BABEL_DATE_FORMATS"]

        self._translator = Translator(
            kwargs.get("default_domain"), config["BABEL_DISABLE_AUTOUPDATE"]
        )
        self._socket = Socket(self)

        db_bind = config["BABEL_DATABASE_BIND"]
        if db_bind is not None:
            from ..translations import I18nKey, I18nMessage
            I18nKey.set_bind(db_bind)
            I18nMessage.set_bind(db_bind)

        elif not EXECUTION:
            from ..translations import I18nKey, I18nMessage

        if config["BABEL_CONFIGURE_JINJA"]:
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

        if config["BABEL_CONFIGURE_SOCKET"]:
            fluid.websocket("/ws/i18n")(self._socket.endpoint)
            fluid.add_source(
                f'<script src="{FRAMEWORK_STATIC}/js/i18n.js" type="module"></script>',
                priority=5
            )

        fluid.startup_hook(lambda: self._translator.translations.startup_hook(
            self, self._translator.domains
        ))
