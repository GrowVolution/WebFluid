from starlette.middleware.sessions import SessionMiddleware

from webfluid.core.constants import DEBUG
from webfluid.utils.logging import factory as log_factory


def add(fluid):
    session_secure = fluid.config["SESSION_COOKIE_SECURE"]
    fluid.add_middleware(
        SessionMiddleware,
        secret_key=fluid.config["SECRET_KEY"],
        session_cookie=fluid.config["SESSION_COOKIE_NAME"],
        https_only=session_secure,
        same_site=fluid.config["SESSION_COOKIE_SAMESITE"]
    )
    if not session_secure and not DEBUG:
        fluid.startup_hook(lambda: log_factory.warning(
            "Session cookies are not secure. "
            "Consider setting SESSION_COOKIE_SECURE=True."
        ))
