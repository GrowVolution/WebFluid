from collections.abc import Callable
from pathlib import Path
from typing import Any
import subprocess

from webfluid import Fluid

proc: subprocess.Popen[Any] | None
root: Path | None
started: float
failures: int
stopping: bool
dev_server: str
dev_prefix: str
watch_job: str
watch_interval: int
quick_exit: int
max_failures: int

def start() -> None: ...
def watch() -> None: ...
def stop() -> None: ...
def supervise() -> None: ...
def startup_hook(fluid: Fluid) -> Callable[[], None]: ...
