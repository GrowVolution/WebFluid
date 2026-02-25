from aioflask import Flask, typing as ft, request
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from multiprocessing import Process
from typing import Callable, Any, TYPE_CHECKING

from webfluid.core.ext import babel
from webfluid.core.context import FluidContext
from webfluid.utils import enabled, is_async_function
from webfluid.utils.config import build_app_config
from webfluid.exceptions import FrameworkException

if TYPE_CHECKING:
    from webfluid import Fluid


class AppLiquid(Flask):
    def __init__(self, import_name: str):
        super().__init__(
            import_name,
            static_folder=None
        )

        self.config.from_object(build_app_config())

        if self.config.get("RATELIMIT_ENABLED", True):
            self.limiter = Limiter(get_remote_address)
            self.limiter.init_app(self)

        self._context_decorator = lambda fn: fn

    def setup(self, fluid: "Fluid"):
        ext_database = enabled("EXT_SQLALCHEMY")
        compat_db = None
        db_updater = None

        if enabled("EXT_BABEL"):
            if not ext_database:
                raise FrameworkException("EXT_BABEL requires EXT_SQLALCHEMY to be be enabled.")
            babel.init_fluid(fluid)

        if ext_database:
            from webfluid.core.ext import migrate, db
            db.init_fluid(fluid)
            compat_db = SQLAlchemy(self, model_class=db.Model)
            migrate.init_app(self, db=compat_db)

            if enabled("DB_AUTOUPDATE"):
                from webfluid.extensions.utils.sqlalchemy import db_autoupdate
                db_updater = Process(target=db_autoupdate, args=(fluid,))
                db_updater.start()

        if enabled("EXT_FST"):
            if not ext_database:
                raise FrameworkException("EXT_FST requires EXT_SQLALCHEMY to be be enabled.")

            from flask_security import SQLAlchemyUserDatastore
            from webfluid.core.ext import security
            from webfluid.extensions.utils.security import (
                init_fst, build_login_form, build_register_form,
                build_user_model, build_role_model, send_security_mail
            )
            init_fst(fluid, compat_db)

            security.init_app(
                self,
                SQLAlchemyUserDatastore(
                    compat_db, build_user_model(), build_role_model()
                ),
                login_form=build_login_form(),
                register_form=build_register_form(),
                send_mail=send_security_mail
            )

        if enabled("EXT_OAUTH"):
            from webfluid.core.ext import oauth
            oauth.init_app(self)

            clients = self.config.get("OAUTH_CLIENTS", {})
            for client, cfg in clients.items():
                oauth.register(
                    name=client,
                    **cfg
                )

        def context_decorator(fn):
            if is_async_function(fn):
                async def wrapper(*args, **kwargs):
                    async with FluidContext(fluid, request):
                        return await fn(*args, **kwargs)
            else:
                def wrapper(*args, **kwargs):
                    with FluidContext(fluid, request):
                        return fn(*args, **kwargs)
            return wrapper
        self._context_decorator = context_decorator

        if db_updater: fluid.startup_hook(db_updater.join)

    def add_url_rule(
        self, rule: str,  endpoint: str | None = None,
        view_func: ft.RouteCallable | None = None,
        provide_automatic_options: bool | None = None,
        **options: Any,
    ):
        if view_func is not None:
            view_func = self._context_decorator(view_func)
        super().add_url_rule(
            rule, endpoint, view_func, provide_automatic_options, **options
        )

    @property
    def limit(self) -> Callable:
        if self.config.get("RATELIMIT_ENABLED", True):
            return self.limiter.limit
        return lambda *_, **__: lambda fn: fn
