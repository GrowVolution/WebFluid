from starlette.middleware.sessions import SessionMiddleware

from webfluid.core.constants import DEBUG
from webfluid.utils.logging import factory as log_factory


def add(fluid):
    session_secure = fluid.config.get(
        "SESSION_COOKIE_SECURE", not DEBUG
    )
    fluid.add_middleware(
        SessionMiddleware,
        secret_key=fluid.config["SECRET_KEY"],
        session_cookie=fluid.config.get(
            "SESSION_COOKIE_NAME", "session"
        ),
        https_only=session_secure,
        same_site=fluid.config.get(
            "SESSION_COOKIE_SAMESITE", "lax"
        )
    )
    if not session_secure and not DEBUG:
        fluid.startup_hook(lambda: log_factory.warning(
            "Session cookies are not secure. "
            "Consider setting SESSION_COOKIE_SECURE=True."
        ))