from typing import TYPE_CHECKING

from webfluid.base import BaseAdditive
from webfluid.core.api import AsyncAdditive
from webfluid.core.app import SyncAdditive
from webfluid.utils.logging import factory as log_factory

if TYPE_CHECKING:
    from webfluid import Fluid


class Additive(BaseAdditive):
    def __init__(self, import_name: str, base: "Additive",
                 required_extensions: list = None, allow_frontend: bool = True):
        super().__init__(import_name, base, required_extensions, allow_frontend)


    def _enable(self, fluid: "Fluid"):
        pass
