from collections.abc import Callable
from typing import Any

from slowapi import Limiter as _Limiter

from webfluid import Fluid

def _disabled(*args: Any, **kwargs: Any) -> Callable[..., Any]: ...

class Limiter:
    enabled: bool
    limiter: _Limiter
    def __init__(self, fluid: Fluid) -> None: ...
    @property
    def limit(self) -> Callable[..., Any]: ...
