from datetime import datetime, UTC
from pathlib import Path
from typing import Optional
import asyncio, hashlib, json, re, subprocess, sys, time

from .logging import factory as log_factory
from webfluid.exceptions import IntegrityGenerationError as GenerationError

_RAW = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")

MANIFEST = "manifest.json"
GENERATOR = "generate.py"


def _entries(data: dict) -> dict:
    if data.get("format") == 2:
        artifacts = data.get("artifacts")
        if not isinstance(artifacts, dict): raise GenerationError("MANIFEST_INVALID")
        return artifacts
    if isinstance(data.get("versions"), list) and isinstance(data.get("artifact"), str):
        return { data["artifact"]: data }
    raise GenerationError("MANIFEST_INVALID")


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


class Artifact:
    def __init__(self, artifact: str, path: Path, url: str, label: str, kind: str = "script",
                 binary: bool = False, version: Optional[str] = None):
        self.artifact = artifact
        self.path = Path(path)
        self.url = url
        self.label = label
        self.kind = kind
        self.binary = binary
        self.version = version

    def digest(self) -> tuple[str, int]:
        served = self.path.read_bytes()
        return hashlib.sha256(served).hexdigest(), len(served)


class IntegrityReference:
    additive: str = ""
    repository: str = ""
    branch: str = "main"
    path: Path = Path("integrity")
    artifacts: dict[str, Artifact] = {}
    update: bool = True
    timeout: int = 60
    _runs: dict = {}
    _lock: Optional[asyncio.Lock] = None

    @classmethod
    def _log(cls, message: str) -> str:
        return f"[{cls.additive}] {message}"

    @classmethod
    def _guard(cls) -> asyncio.Lock:
        if cls._lock is None: cls._lock = asyncio.Lock()
        return cls._lock

    @staticmethod
    def _matched(reference: dict, artifact: str, value: str) -> tuple[dict, Optional[str]]:
        entry = (reference.get("artifacts") or {}).get(artifact) or {}
        versions = entry.get("versions") or {}
        return entry, next((version for version, digest in versions.items() if digest == value), None)

    @classmethod
    def setup(cls, additive: str, repo: str, path: str | Path, artifacts: list[Artifact], root: str | Path,
              update: bool = True, timeout: int = 60, branch: str = "main"):
        target = Path(path)
        cls.additive = additive
        cls.repository = repo or ""
        cls.branch = branch
        cls.path = target if target.is_absolute() else Path(root).resolve() / target
        cls.artifacts = { artifact.artifact: artifact for artifact in artifacts }
        cls.update = update
        cls.timeout = max(5, int(timeout))
        cls._runs = {}
        cls._lock = None

    @classmethod
    def manifest_url(cls) -> Optional[str]:
        match = _RAW.match(cls.repository or "")
        if not match: return None
        return f"https://raw.githubusercontent.com/{match.group(1)}/{match.group(2)}/{cls.branch}/{MANIFEST}"

    @classmethod
    def refresh(cls) -> dict:
        from git import Repo, GitCommandError, InvalidGitRepositoryError, NoSuchPathError
        if not cls.repository: raise GenerationError("REFERENCE_UNCONFIGURED")
        state = { "updated": False, "dirty": False, "error": None }
        try:
            if not cls.path.exists() or not any(cls.path.iterdir()):
                if not cls.update: raise GenerationError("REFERENCE_MISSING")
                Repo.clone_from(cls.repository, cls.path, depth=50, kill_after_timeout=cls.timeout)
                state["updated"] = True
            repo = Repo(cls.path)
            state["dirty"] = repo.is_dirty(untracked_files=False)
            if cls.update and not state["dirty"] and repo.remotes:
                repo.git.fetch("origin", kill_after_timeout=cls.timeout)
                try:
                    repo.git.merge("--ff-only", f"origin/{cls.branch}", kill_after_timeout=cls.timeout)
                    state["updated"] = True
                except GitCommandError as exc:
                    state["error"] = "FAST_FORWARD_FAILED"
                    log_factory.warning(cls._log(f"The integrity reference could not be fast-forwarded: {exc}"))
            state["commit"] = repo.head.commit.hexsha if repo.head.is_valid() else None
        except GenerationError:
            raise
        except (GitCommandError, InvalidGitRepositoryError, NoSuchPathError, OSError) as exc:
            state["error"] = "REFERENCE_UPDATE_FAILED"
            state["detail"] = str(exc)[:200]
            try: state["commit"] = Repo(cls.path).head.commit.hexsha
            except Exception: state["commit"] = None
        return state

    @classmethod
    def generate(cls) -> dict:
        generator = cls.path / GENERATOR
        if not generator.is_file(): raise GenerationError("GENERATOR_MISSING")
        manifest = cls.path / MANIFEST
        started = time.time()
        try:
            completed = subprocess.run(
                [sys.executable, "-I", str(generator)], cwd=str(cls.path), capture_output=True,
                text=True, timeout=cls.timeout, check=False
            )
        except subprocess.TimeoutExpired as exc:
            raise GenerationError("GENERATOR_TIMEOUT") from exc
        except OSError as exc:
            raise GenerationError("GENERATOR_FAILED", str(exc)) from exc
        if completed.returncode != 0:
            raise GenerationError("GENERATOR_FAILED", (completed.stderr or completed.stdout or "")[-400:])
        if not manifest.is_file() or manifest.stat().st_mtime < started - 1:
            raise GenerationError("GENERATOR_STALE")
        try: data = json.loads(manifest.read_text(encoding="utf-8"))
        except ValueError as exc: raise GenerationError("MANIFEST_INVALID") from exc
        if not isinstance(data, dict): raise GenerationError("MANIFEST_INVALID")

        artifacts = {}
        for artifact, entry in _entries(data).items():
            if not isinstance(entry, dict) or not isinstance(entry.get("versions"), list):
                raise GenerationError("MANIFEST_INVALID", str(artifact))
            known = cls.artifacts.get(artifact)
            versions = {}
            for item in entry["versions"]:
                source = cls.path / str(item.get("file") or "")
                if not source.is_file() or not source.resolve().is_relative_to(cls.path.resolve()):
                    raise GenerationError("MANIFEST_INVALID", str(item.get("file")))
                content = source.read_bytes()
                local = hashlib.sha256(content if known and known.binary else normalized(content)).hexdigest()
                if local != item.get("sha256"):
                    raise GenerationError("NOT_REPRODUCIBLE", f"{artifact} {item.get('version')}")
                versions[item["version"]] = local
            artifacts[artifact] = { "versions": versions, "latest": entry.get("latest") }
        return { "artifacts": artifacts, "returncode": completed.returncode }

    @classmethod
    async def compute(cls, run: str) -> dict:
        async with cls._guard():
            if run in cls._runs: return cls._runs[run]
            loop = asyncio.get_running_loop()
            try:
                state = await loop.run_in_executor(None, cls.refresh)
                generated = await loop.run_in_executor(None, cls.generate)
                reference = { "status": "ok", **state, **generated }
            except GenerationError as exc:
                reference = { "status": "unavailable", "error": exc.code, "detail": exc.detail[:200] }
                if exc.code != "REFERENCE_UNCONFIGURED":
                    log_factory.warning(cls._log(f"The integrity reference is unavailable: {exc.code} {exc.detail[:200]}"))
            except Exception as exc:
                reference = { "status": "unavailable", "error": "REFERENCE_FAILED" }
                log_factory.exception(exc, cls._log("Computing the integrity reference failed."))
            reference["checked_at"] = now()
            reference["finished"] = time.time()
            cls._runs = { key: value for key, value in list(cls._runs.items())[-4:] }
            cls._runs[run] = reference
            return reference

    @classmethod
    async def ensure_fresh(cls, interval: int) -> dict:
        latest = cls.latest()
        if latest and time.time() - latest.get("finished", 0) < interval: return latest
        return await cls.compute(f"local:{int(time.time())}")

    @classmethod
    def latest(cls) -> Optional[dict]:
        return list(cls._runs.values())[-1] if cls._runs else None

    @classmethod
    def served_versions(cls) -> dict[str, Optional[str]]:
        latest = cls.latest() or {}
        return { artifact: cls._matched(latest, artifact, item.digest()[0])[1]
                 for artifact, item in cls.artifacts.items() }

    @classmethod
    async def record(cls, run: str, artifact: Artifact) -> dict:
        value, size = artifact.digest()
        reference = await cls.compute(run)
        entry, served_version = cls._matched(reference, artifact.artifact, value)
        versions = entry.get("versions") or {}
        if reference["status"] != "ok" or not entry: provenance = "reference-unavailable"
        elif served_version: provenance = "reference-match"
        else: provenance = "reference-mismatch"
        return {
            "id": artifact.artifact,
            "additive": cls.additive,
            "type": artifact.kind,
            "algorithm": "sha256",
            "hash": value,
            "size": size,
            "version": served_version or artifact.version or "unknown",
            "served_version": served_version,
            "latest_version": entry.get("latest"),
            "url": artifact.url,
            "served": True,
            "computed_at": now(),
            "label": artifact.label,
            "reference": {
                "source": "git", "url": cls.repository or None, "commit": reference.get("commit"),
                "manifest": cls.manifest_url(),
                "hash": versions.get(served_version) if served_version else None
            },
            "provenance": { "status": provenance },
            "context": {
                "generator": GENERATOR, "run": run, "reference_status": reference["status"],
                "error": reference.get("error"), "dirty": reference.get("dirty"),
                "updated": reference.get("updated"), "reproduced": reference["status"] == "ok"
            }
        }

    @classmethod
    async def provide(cls, data) -> list[dict]:
        run = (data or {}).get("run") if isinstance(data, dict) else None
        run = str(run or now())
        return [await cls.record(run, artifact) for artifact in cls.artifacts.values()]

    @classmethod
    def artifact_status(cls, artifact: str) -> dict:
        item = cls.artifacts[artifact]
        value, size = item.digest()
        entry, served = cls._matched(cls.latest() or {}, artifact, value)
        return {
            "id": artifact, "url": item.url, "hash": value, "size": size,
            "served_version": served, "latest_version": entry.get("latest")
        }

    @classmethod
    async def status(cls) -> dict:
        latest = cls.latest() or {}
        return {
            "reference": latest.get("status", "pending"),
            "checked_at": latest.get("checked_at"),
            "repository": cls.repository or None,
            "manifest": cls.manifest_url(),
            "artifacts": [cls.artifact_status(artifact) for artifact in cls.artifacts]
        }
