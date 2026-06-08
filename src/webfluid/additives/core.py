from jinja2 import ChoiceLoader
from importlib import import_module
from typing import TYPE_CHECKING

from webfluid.core.additive import Additive
from webfluid.core.constants import DEBUG, DEV_AUTO_INSTALL
from webfluid.utils.framework import enabled
from webfluid.utils.logging import factory as log_factory

if TYPE_CHECKING:
    from webfluid import Fluid


async def register_additives(fluid: "Fluid"):
    from webfluid.core.constants import ADDITIVES
    loaders = []

    async def register():
        nonlocal loaders

        from .utils import installed_additives
        for additive_info in installed_additives(fluid.additive_root, True):
            additive_id = additive_info[0]
            if not enabled(additive_id):
                continue

            try:
                mod = import_module(f"additives.{additive_info[2]}")
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
                loaders.append(additive.loader)
                log_factory.log(f"[{additive.name}] Additive successfully registered.")
            except Exception as e:
               log_factory.exception(e, f"[{additive.name}] Failed registering additive.")

    loaders.append(fluid.app_loader)
    if ADDITIVES: await register()
    loaders.append(fluid.framework_loader)

    fluid.jinja_env.loader = ChoiceLoader(loaders)
