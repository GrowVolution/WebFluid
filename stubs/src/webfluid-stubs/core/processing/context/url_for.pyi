from collections.abc import Callable
from typing import Any

from webfluid import Fluid

def offline_url(
    fluid: Fluid, endpoint: str, external: bool, path_params: dict[str, Any]
) -> str: ...
def url_for(fluid: Fluid) -> Callable[..., str]: ...
