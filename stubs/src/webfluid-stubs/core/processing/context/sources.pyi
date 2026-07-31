from collections.abc import Callable

from markupsafe import Markup

from webfluid import Fluid

def get_source_callables(
    fluid: Fluid
) -> tuple[Callable[[], Markup | str], Callable[[], str]]: ...
