from collections.abc import Callable, Coroutine
from typing import Any
import subprocess

from webfluid import Fluid

proc: subprocess.Popen[Any] | None

def startup_hook(fluid: Fluid) -> Callable[[], Coroutine[Any, Any, None]]: ...
