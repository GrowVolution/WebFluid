from collections.abc import Callable
from typing import Any
import subprocess

from webfluid import Fluid

proc: subprocess.Popen[Any] | None
dev_server: str
dev_prefix: str

def stop() -> None: ...
def startup_hook(fluid: Fluid) -> Callable[[], None]: ...
