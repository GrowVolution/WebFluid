from importlib import import_module
from datetime import datetime
from typing import TYPE_CHECKING
import os

from webfluid.additives import installed_additives
from webfluid.utils import enabled
from webfluid.utils.logging import factory as log_factory

if TYPE_CHECKING:
    from webfluid import Fluid


def _fix_missing(migrations: str):
    versions_path = os.path.join(migrations, "versions")
    if os.path.isdir(versions_path):
        files = sorted(
            [f for f in os.listdir(versions_path) if f.endswith(".py")],
            key=lambda x: os.path.getmtime(os.path.join(versions_path, x)),
        )
        if files:
            latest_file = os.path.join(versions_path, files[-1])
            with open(latest_file, "r", encoding="utf-8") as f:
                content = f.read()

            import_str = f"import flask_security"
            if "flask_security" in content and import_str not in content:
                content = f"{import_str}\n{content}"
                with open(latest_file, "w", encoding="utf-8") as f:
                    f.write(content)
                log_factory.debug(f"[MIGRATE] Fixed missing flask_security import in {latest_file}")


def init_models(fluid: "Fluid"):
    for file in (fluid.framework_root / "app" / "models").rglob("*.py"):
        if file.stem == "__init__" or not file.stem.endswith("_models"):
            continue
        import_module(f"webfluid.app.models.{file.stem}")

    additives = fluid.app_root / "additives"
    if not additives.exists() or not additives.is_dir(): return
    for additive_info in installed_additives(additives, False):
        m, _, p = additive_info
        if not enabled(m): continue
        try:
            mod = import_module(f"additives.{p}")
            additive = getattr(mod, "additive", None)
            if additive and not additive.is_base:
                additive.init_models()
        except ModuleNotFoundError: pass


def db_autoupdate(fluid: "Fluid"):
    message = f"App-Factory autoupdate - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    with fluid.app.app_context():
        from flask_migrate import init as fm_init, migrate as fm_migrate, upgrade as fm_upgrade
        migrations = os.path.join(fluid.app.root_path, "migrations")
        if not os.path.isdir(migrations):
            fm_init(directory=migrations)
        fm_migrate(message=message, directory=migrations)

        _fix_missing(migrations)
        fm_upgrade(directory=migrations)
