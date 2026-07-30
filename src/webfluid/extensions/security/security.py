from webfluid.core.constants import DEBUG, EXECUTION
from webfluid.extensions.base import FluidExtension
from webfluid.extensions.sqlalchemy.utils import update_metadata
from webfluid.utils.logging import factory as log_factory
from webfluid.exceptions import FrameworkException

_not_initialized = "Security.expand_fluid() has not been called."


class Security(FluidExtension):
    def __init__(self, fluid=None):
        self._user_service = None
        self._token_service = None
        self._hash_service = None
        self._oauth_service = None

        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        secret = fluid.config.get("SECURITY_SECRET")
        if EXECUTION:
            if not secret and DEBUG:
                fluid.startup_hook(lambda: log_factory.warning(
                    "[Security] Missing SECURITY_SECRET, using a consistent debug secret."
                ))
                secret = "super-secret-key"
            elif not secret:
                raise ValueError("SECURITY_SECRET must be configured in production.")
        else:
            secret = ""

        from .services import UserService, TokenService, HashService, OAuthService
        self._token_service = TokenService(
            secret, fluid.config.get("SECURITY_TOKEN_MAX_AGE", 3600),
            fluid.config.get("SECURITY_CSRF_COOKIE_NAME", "csrf_token"),
            fluid.config.get("SECURITY_CSRF_COOKIE_SECURE", True)
        )
        self._user_service = UserService(self._token_service)
        self._hash_service = HashService(
            fluid.config.get("SECURITY_HASHER_TIME_COST", 3),
            fluid.config.get("SECURITY_HASHER_MEMORY_COST", 65536),
            fluid.config.get("SECURITY_HASHER_PARALLELISM", 4)
        )
        self._oauth_service = OAuthService(
            fluid.config.get("SECURITY_OAUTH_CLIENTS", {})
        )

        bind = fluid.config.get("SECURITY_MODELS_DB_BIND")
        if bind:
            from .models.user import (
                User, Identity, Role, Permission,
                TOTPSecret, WebAuthnCredential, BackupCode,
                user_roles, role_permissions
            )
            User.set_bind(bind)
            Identity.set_bind(bind)
            Role.set_bind(bind)
            Permission.set_bind(bind)
            TOTPSecret.set_bind(bind)
            WebAuthnCredential.set_bind(bind)
            BackupCode.set_bind(bind)
            update_metadata(user_roles, target_bind=bind)
            update_metadata(role_permissions, target_bind=bind)

            from .models.token import ExpiredToken
            ExpiredToken.set_bind(bind)

    @property
    def user_service(self):
        if self._user_service is None:
            raise FrameworkException(_not_initialized)
        return self._user_service

    @property
    def token_service(self):
        if self._token_service is None:
            raise FrameworkException(_not_initialized)
        return self._token_service

    @property
    def hash_service(self):
        if self._hash_service is None:
            raise FrameworkException(_not_initialized)
        return self._hash_service

    @property
    def oauth_service(self):
        if self._oauth_service is None:
            raise FrameworkException(_not_initialized)
        return self._oauth_service
