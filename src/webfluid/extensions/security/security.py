from webfluid.core.constants import DEBUG, EXECUTION
from webfluid.extensions.base import Delegated, FluidExtension
from webfluid.extensions.security.utils import PasswordPolicy, set_policy
from webfluid.extensions.sqlalchemy.utils import update_metadata
from webfluid.utils.logging import factory as log_factory

_models = (
    "User", "Identity", "Role", "Permission",
    "TOTPSecret", "WebAuthnCredential", "BackupCode"
)


def _resolve_secret(fluid):
    secret = fluid.config["SECURITY_SECRET"]
    if not EXECUTION: return ""

    if secret: return secret

    if not DEBUG:
        raise ValueError("SECURITY_SECRET must be configured in production.")

    fluid.startup_hook(lambda: log_factory.warning(
        "[Security] Missing SECURITY_SECRET, using a consistent debug secret."
    ))
    return "super-secret-key"


def _bind_models(bind):
    from .models import user as models
    from .models.token import ExpiredToken

    for name in _models: getattr(models, name).set_bind(bind)
    update_metadata(models.user_roles, target_bind=bind)
    update_metadata(models.role_permissions, target_bind=bind)
    ExpiredToken.set_bind(bind)


class Security(FluidExtension):
    user_service = Delegated("_user_service")
    token_service = Delegated("_token_service")
    hash_service = Delegated("_hash_service")
    oauth_service = Delegated("_oauth_service")

    def __init__(self, fluid=None):
        self._user_service = None
        self._token_service = None
        self._hash_service = None
        self._oauth_service = None

        super().__init__(fluid)

    def expand_fluid(self, fluid, *_, **__):
        config = fluid.config
        secret = _resolve_secret(fluid)

        from .services import UserService, TokenService, HashService, OAuthService
        self._token_service = TokenService(
            secret, config["SECURITY_TOKEN_MAX_AGE"],
            config["SECURITY_CSRF_COOKIE_NAME"],
            config["SECURITY_CSRF_COOKIE_SECURE"]
        )
        self._user_service = UserService(self._token_service)
        self._hash_service = HashService(
            config["SECURITY_HASHER_TIME_COST"],
            config["SECURITY_HASHER_MEMORY_COST"],
            config["SECURITY_HASHER_PARALLELISM"],
            config["SECURITY_HASHER_THREADS"]
        )
        self._oauth_service = OAuthService(config["SECURITY_OAUTH_CLIENTS"])

        set_policy(PasswordPolicy(
            config["SECURITY_PASSWORD_MIN_LENGTH"],
            config["SECURITY_PASSWORD_REQUIREMENTS"]
        ))

        bind = config["SECURITY_MODELS_DB_BIND"]
        if bind: _bind_models(bind)
