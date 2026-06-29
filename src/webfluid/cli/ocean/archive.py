from pathlib import Path
import io, re, tarfile, hashlib

_JUNK_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".idea", ".vscode", ".cache"
}
_JUNK_FILES = { ".ds_store", "thumbs.db", "desktop.ini" }
_JUNK_SUFFIXES = (".pyc", ".pyo", ".pyd", ".swp", ".swo", ".log", ".tmp", "~")

_IGNORE_NAME = ".gitignore"


def _is_junk(rel: str) -> bool:
    segments = rel.split("/")
    name = segments[-1]
    lower = name.lower()
    for segment in segments[:-1]:
        if segment in _JUNK_DIRS or segment.endswith(".egg-info"):
            return True
    if name in _JUNK_DIRS: return True
    if lower in _JUNK_FILES: return True
    return any(lower.endswith(suffix) for suffix in _JUNK_SUFFIXES)


def _glob_to_regex(pattern: str, anchored: bool) -> re.Pattern:
    out = ""
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "*" and i + 1 < len(pattern) and pattern[i + 1] == "*":
            out += ".*"
            i += 2
            if i < len(pattern) and pattern[i] == "/": i += 1
            continue
        if char == "*": out += "[^/]*"
        elif char == "?": out += "[^/]"
        elif char in "\\^$.|+()[]{}": out += "\\" + char
        else: out += char
        i += 1
    prefix = "^" if anchored else "(?:^|/)"
    return re.compile(prefix + out + "$")


def _parse_rule(raw: str):
    trimmed = raw.rstrip("\r").strip()
    if not trimmed or trimmed.startswith("#"): return None
    if re.fullmatch(r"\[[^\]]*\]", trimmed): return None

    line = trimmed
    negate = False
    if line.startswith("!"): negate = True; line = line[1:]

    dir_only = False
    if line.endswith("/"): dir_only = True; line = line[:-1]

    anchored = False
    if line.startswith("/"): anchored = True; line = line[1:]
    elif "/" in line: anchored = True

    if not line: return None
    return negate, dir_only, _glob_to_regex(line, anchored)


def _collect_ignores(root: Path, rels: list[str]) -> list[tuple[str, list]]:
    ignores = []
    for rel in rels:
        if rel != _IGNORE_NAME and not rel.endswith("/" + _IGNORE_NAME):
            continue
        base = rel[:-len(_IGNORE_NAME)].rstrip("/")
        rules = []
        text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        for raw in text.split("\n"):
            rule = _parse_rule(raw)
            if rule: rules.append(rule)
        ignores.append((base, rules))
    ignores.sort(key=lambda ig: 0 if ig[0] == "" else len(ig[0].split("/")))
    return ignores


def _is_ignored(rel: str, ignores: list[tuple[str, list]]) -> bool:
    segments = rel.split("/")
    ignored = False
    for depth in range(1, len(segments) + 1):
        sub = "/".join(segments[:depth])
        is_dir = depth < len(segments)
        for base, rules in ignores:
            if base != "" and sub != base and not sub.startswith(base + "/"):
                continue
            local = sub if base == "" else sub[len(base) + 1:]
            if not local: continue
            for negate, dir_only, regex in rules:
                if dir_only and not is_dir: continue
                if regex.search(local): ignored = not negate
        if is_dir and ignored: return True
    return ignored


def _pack(entries: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(
            fileobj=buffer, mode="w",
            format=tarfile.USTAR_FORMAT
    ) as tar:
        for name, data in sorted(entries, key=lambda entry: entry[0]):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            info.mtime = 0
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def selected_files(root: Path) -> list[str]:
    rels = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*") if path.is_file()
    ]
    ignores = _collect_ignores(root, rels)
    return sorted(
        rel for rel in rels
        if not _is_junk(rel) and not _is_ignored(rel, ignores)
    )


def build_archive(root: Path) -> bytes:
    entries = [
        (rel, (root / rel).read_bytes())
        for rel in selected_files(root)
    ]
    return _pack(entries)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
