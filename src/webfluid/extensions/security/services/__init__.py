from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid.extensions.security.services.token import TokenService
    from webfluid.extensions.security.services.user import UserService
    from webfluid.extensions.security.services.oauth import OAuthService
    from webfluid.extensions.security.services.hashing import HashService

__all__ = ["TokenService", "UserService", "OAuthService", "HashService"]


def __getattr__(name):
    if name == "TokenService":
        from .token import TokenService
        return TokenService

    if name == "UserService":
        from .user import UserService
        return UserService

    if name == "OAuthService":
        from .oauth import OAuthService
        return OAuthService

    if name == "HashService":
        from .hashing import HashService
        return HashService

    raise AttributeError(name)
