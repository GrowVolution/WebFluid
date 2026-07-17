from collections.abc import Callable

from webfluid.core.fluid import Fluid

def setup_and_get_locale_fn(fluid: Fluid) -> Callable[[], str]: ...
