from functools import wraps
from importlib import import_module
import os

from webfluid.core.constants import DEBUG, DEV_AUTO_INSTALL


def require_extensions(*extensions):
    def decorator(fn):
        from ..core import enabled, async_result
        from ..logging import factory as log_factory

        @wraps(fn)
        async def wrapper(*args, **kwargs):
            for ext in extensions:
                if not isinstance(ext, str):
                    log_factory.warning(f"Invalid extension '{ext}'.")
                    continue

                if not enabled(f"EXT_{ext.upper()}"):
                    raise RuntimeError(f"Extension '{ext}' is not enabled.")
            return await async_result(fn(*args, **kwargs))

        return wrapper
    return decorator


async def register_additives(fluid):
    from webfluid.core.additive import Additive
    from .loading import installed_additives
    from ..core import enabled
    from ..logging import factory as log_factory
    from ..cli import progress_bar

    total = os.getenv("ENABLED_ADDITIVES")
    total = int(total) if total else None

    with progress_bar("Additive registration phase", total, leave=False) as bar:
        for additive_info in installed_additives(fluid.additive_root, True):
            additive_id = additive_info[0]
            if not enabled(additive_id):
                continue

            try: mod = import_module(f"additives.{additive_info[2]}")
            except ModuleNotFoundError as e:
                log_factory.exception(e, f"Could not import additive '{additive_id}' for app '{fluid.name}'.")
                continue

            additive = getattr(mod, "additive", None)
            if not isinstance(additive, Additive):
                log_factory.error(f"Missing 'additive: Additive' in additive package of '{additive_id}'.")
                continue

            try:
                log_factory.log(f"Registering: {additive}")
                if DEBUG and DEV_AUTO_INSTALL: additive.install()
                await additive.enable(fluid)
                log_factory.log(f"[{additive.name}] Additive successfully registered.")
            except Exception as e:
                log_factory.exception(e, f"[{additive.name}] Failed registering additive.")

            bar.update()
