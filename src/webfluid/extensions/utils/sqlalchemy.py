from importlib import import_module
from datetime import datetime
from typing import TYPE_CHECKING

from webfluid.additives import installed_additives
from webfluid.utils import enabled

if TYPE_CHECKING:
    from webfluid import Fluid


def database_uris(uri: str) -> tuple[str, str]:
    if "+" in uri.split("://")[0]:
        raise ValueError(f"Invalid database URI '{uri}': Please do not define drivers.")

    if uri.startswith("sqlite:"):
        sync_uri = uri
        async_uri = uri.replace("sqlite", "sqlite+aiosqlite")
    elif uri.startswith("postgresql:"):
        sync_uri = uri.replace("postgresql", "postgresql+psycopg2")
        async_uri = uri.replace("postgresql", "postgresql+asyncpg")
    elif uri.startswith("mysql:"):
        sync_uri = uri.replace("mysql", "mysql+pymysql")
        async_uri = uri.replace("mysql", "mysql+aiomysql")
    else:
        raise ValueError(f"Invalid database URI '{uri}': Unsupported database type.")

    return sync_uri, async_uri


def init_models(fluid: "Fluid"):
    for file in (fluid.framework_root / "app" / "models").rglob("*.py"):
        if file.stem == "__init__" or not file.stem.endswith("_models"):
            continue
        import_module(f"webfluid.models.{file.stem}")

    additives = fluid.app_root / "additives"
    if not additives.exists() or not additives.is_dir(): return
    for additive in installed_additives(additives):
        a, _, p = additive
        if not enabled(a): continue
        try:
            mod = import_module(f"additives.{p}")
            additive = getattr(mod, "additive", None)
            if additive and not additive.is_base:
                additive.init_models()
        except ModuleNotFoundError: pass


def db_autoupdate(fluid: "Fluid"):
    message = f"App-Factory autoupdate - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    # TODO: Implement Autoupdate