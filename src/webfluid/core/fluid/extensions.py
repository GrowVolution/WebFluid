from webfluid.core.constants import (
    EXECUTION,
    FRAMEWORK_ID,

    EXT_SCHEDULING,
    EXT_SQLALCHEMY,
    EXT_BABEL,
    EXT_SECURITY,
    EXT_EVENTS,
    EXT_CACHE,
    EXT_MAIL,
    EXT_JWT
)
from webfluid.core.ext import (
    scheduler,
    db,
    babel,
    security,
    events,
    cache,
    mail,
    jwt
)


def enable_extensions(fluid):
    if EXT_SCHEDULING: fluid.startup_hook(scheduler.start)
    if EXT_SQLALCHEMY: db.expand_fluid(fluid)

    if EXT_BABEL:
        babel.expand_fluid(fluid)

        if EXECUTION:
            from webfluid.fluid.i18n import translations
            babel.register_domain(FRAMEWORK_ID)
            babel.update_translations(FRAMEWORK_ID, translations)

    if EXT_SECURITY: security.expand_fluid(fluid)
    if EXT_EVENTS: events.expand_fluid(fluid)
    if EXT_CACHE: cache.expand_fluid(fluid)
    if EXT_MAIL: mail.expand_fluid(fluid)
    if EXT_JWT: jwt.expand_fluid(fluid)
