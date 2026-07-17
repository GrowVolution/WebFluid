from collections.abc import Awaitable, Callable

from webfluid import Fluid
from webfluid.core.additive.main import Additive

def _enable(additive: Additive, fluid: Fluid) -> None: ...
def create_enable(additive: Additive) -> Callable[[Fluid], Awaitable[None]]: ...
