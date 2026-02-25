from importlib import import_module
from flask_security.forms import LoginForm, RegisterFormV2
from flask_security.models import fsqla_v3 as fsqla
from typing import Callable, TYPE_CHECKING
import inspect

from webfluid.additives import installed_additives
from webfluid.core.ext import db, mail
from webfluid.utils import check_priority, build_sorted_tuple, enabled

if TYPE_CHECKING:
    from webfluid import Fluid
    import flask_sqlalchemy as fsa

_login_forms: dict[int, list[type]] = {}
_register_forms: dict[int, list[type]] = {}

_user_mixins: dict[int, list[type]] = {}
_role_mixins: dict[int, list[type]] = {}


def _valid_mixin(cls: type, kind: str):
    if not inspect.isclass(cls):
        raise TypeError(f"{kind} mixin must be a class.")
    if hasattr(cls, "__tablename__"):
        raise TypeError(f"{kind} mixins must not define tables.")


def init_fst(fluid: "Fluid", compat_db: "fsa.SQLAlchemy"):
    fsqla.FsModels.set_db_info(compat_db)

    additives = fluid.app_root / "additives"
    if not additives.exists() or not additives.is_dir(): return
    for additive_info in installed_additives(additives, False):
        m, _, p = additive_info
        if not enabled(m): continue
        try:
            import_module(f"additives.{p}.fst_forms")
            import_module(f"additives.{p}.models.fst_mixins")
        except ModuleNotFoundError: pass


def login_form(priority: int = 1) -> Callable:
    check_priority(priority)

    def decorator(cls):
        if not priority in _login_forms:
            _login_forms[priority] = []
        _login_forms[priority].append(cls)
        return cls

    return decorator


def register_form(priority: int = 1) -> Callable:
    check_priority(priority)

    def decorator(cls):
        if not priority in _register_forms:
            _register_forms[priority] = []
        _register_forms[priority].append(cls)
        return cls

    return decorator


def build_login_form() -> type:
    bases = tuple()
    for configs in build_sorted_tuple(_login_forms):
        bases += tuple(configs)

    return type(
        "ExtendedLoginForm",
        bases + (LoginForm, ),
        {}
    )


def build_register_form() -> type:
    bases = tuple()
    for configs in build_sorted_tuple(_register_forms):
        bases += tuple(configs)

    return type(
        "ExtendedRegisterForm",
        bases + (RegisterFormV2, ),
        {}
    )


def user_mixin(priority: int = 1) -> Callable:
    check_priority(priority)

    def decorator(cls):
        _valid_mixin(cls, "User")
        if priority not in _user_mixins:
            _user_mixins[priority] = []
        _user_mixins[priority].append(cls)
        return cls
    return decorator


def role_mixin(priority: int = 1) -> Callable:
    check_priority(priority)

    def decorator(cls):
        _valid_mixin(cls, "Role")
        if priority not in _role_mixins:
            _role_mixins[priority] = []
        _role_mixins[priority].append(cls)
        return cls
    return decorator


def build_user_model() -> type:
    bases = tuple()
    for mixins in build_sorted_tuple(_user_mixins):
        bases += tuple(mixins)

    return type(
        "User",
        bases + (db.Model, fsqla.FsUserMixin),
        {}
    )


def build_role_model() -> type:
    bases = tuple()
    for mixins in build_sorted_tuple(_role_mixins):
        bases += tuple(mixins)

    return type(
        "Role",
        bases + (db.Model, fsqla.FsRoleMixinV2),
        {}
    )


def send_security_mail(msg: dict):
    body = { "plain": msg["body"] }
    if "html" in msg: body["html"] = msg["html"]
    mail.send(
        to_email=msg["recipient"],
        subject=msg["subject"],
        body=body,
        from_email=msg["sender"]
    )
