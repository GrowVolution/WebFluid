import asyncio, re
from pathlib import Path
from typing import Any, Optional

from webfluid.exceptions import IntegrityGenerationError as GenerationError

MANIFEST: str
GENERATOR: str
_RAW: re.Pattern[str]

def now() -> str: ...
def normalized(data: bytes) -> bytes: ...
def _entries(data: dict[str, Any]) -> dict[str, Any]: ...

class Artifact:
    artifact: str
    path: Path
    url: str
    label: str
    kind: str
    binary: bool
    version: Optional[str]
    def __init__(
        self, artifact: str, path: Path, url: str, label: str, kind: str = "script",
        binary: bool = False, version: Optional[str] = None
    ) -> None: ...
    def digest(self) -> tuple[str, int]: ...

class IntegrityReference:
    additive: str
    repository: str
    branch: str
    path: Path
    artifacts: dict[str, Artifact]
    update: bool
    timeout: int
    _runs: dict[str, dict[str, Any]]
    _lock: Optional[asyncio.Lock]
    @classmethod
    def setup(
        cls, additive: str, repo: str, path: str | Path, artifacts: list[Artifact], root: str | Path,
        update: bool = True, timeout: int = 60, branch: str = "main"
    ) -> None: ...
    @classmethod
    def _log(cls, message: str) -> str: ...
    @classmethod
    def manifest_url(cls) -> Optional[str]: ...
    @classmethod
    def refresh(cls) -> dict[str, Any]: ...
    @classmethod
    def generate(cls) -> dict[str, Any]: ...
    @classmethod
    def _guard(cls) -> asyncio.Lock: ...
    @classmethod
    async def compute(cls, run: str) -> dict[str, Any]: ...
    @classmethod
    async def ensure_fresh(cls, interval: int) -> dict[str, Any]: ...
    @classmethod
    def latest(cls) -> Optional[dict[str, Any]]: ...
    @staticmethod
    def _matched(reference: dict[str, Any], artifact: str, value: str) -> tuple[dict[str, Any], Optional[str]]: ...
    @classmethod
    def served_versions(cls) -> dict[str, Optional[str]]: ...
    @classmethod
    async def record(cls, run: str, artifact: Artifact) -> dict[str, Any]: ...
    @classmethod
    async def provide(cls, data: Any) -> list[dict[str, Any]]: ...
    @classmethod
    def artifact_status(cls, artifact: str) -> dict[str, Any]: ...
    @classmethod
    async def status(cls) -> dict[str, Any]: ...
