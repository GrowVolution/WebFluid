from typing import TYPE_CHECKING

from webfluid.extensions.base import FluidExtension

if TYPE_CHECKING:
    from webfluid.core.fluid import Fluid


class Security(FluidExtension):
    def __init__(self, fluid: "Fluid | None" = None):

        super().__init__(fluid)
