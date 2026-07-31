from webfluid.core import ext
from webfluid.core.identity import FRAMEWORK_ID
from webfluid.core.constants import (
    EXECUTION,

    EXT_SCHEDULING,
    EXT_SQLALCHEMY,
    EXT_BABEL,
    EXT_SECURITY,
    EXT_EVENTS,
    EXT_CACHE,
    EXT_MAIL,
    EXT_JWT
)


def enable_extensions(fluid):
    if EXT_SCHEDULING: fluid.startup_hook(ext.scheduler.start)
    if EXT_SQLALCHEMY: ext.db.expand_fluid(fluid)

    if EXT_BABEL:
        ext.babel.expand_fluid(fluid)

        if EXECUTION:
            from webfluid.fluid.i18n import translations
            ext.babel.register_domain(FRAMEWORK_ID)
            ext.babel.update_translations(FRAMEWORK_ID, translations)

    if EXT_SECURITY: ext.security.expand_fluid(fluid)
    if EXT_EVENTS: ext.events.expand_fluid(fluid)
    if EXT_CACHE: ext.cache.expand_fluid(fluid)
    if EXT_MAIL: ext.mail.expand_fluid(fluid)
    if EXT_JWT: ext.jwt.expand_fluid(fluid)
