from collections.abc import Callable

from webfluid.core.fluid import Fluid

def get_source_callables(fluid: Fluid) -> tuple[Callable[[], str], Callable[[], str]]: ...
