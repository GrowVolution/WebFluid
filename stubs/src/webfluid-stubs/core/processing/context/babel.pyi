from collections.abc import Callable

from babel import Locale

from webfluid import Fluid

def setup_and_get_locale_fn(fluid: Fluid) -> Callable[[], Locale | str]: ...
