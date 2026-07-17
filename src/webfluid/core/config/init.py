from webfluid.core.constants import FRAMEWORK_ID
from webfluid.utils.core import enabled, try_import
from webfluid.utils.additives import installed_additives


def init_configs(fluid):
    try_import(f"{FRAMEWORK_ID}.config")

    additives = fluid.project_root / "additives"
    if not additives.exists() or not additives.is_dir(): return
    for additive in installed_additives(additives, cache=False):
        a, _, p = additive
        if not enabled(a): continue
        try_import(f"additives.{p}.config")
