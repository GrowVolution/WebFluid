
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
