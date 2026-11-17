from pathlib import Path
import hashlib, io, os, re, stat, tarfile

SNIFF_LIMIT = 1024 * 1024

_JUNK_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".idea", ".vscode", ".cache"
}
_JUNK_FILES = { ".ds_store", "thumbs.db", "desktop.ini" }
_JUNK_SUFFIXES = (".pyc", ".pyo", ".pyd", ".swp", ".swo", ".log", ".tmp", "~")

_IGNORE_NAME = ".gitignore"
_CLASSES = {
    "alnum": "a-zA-Z0-9", "alpha": "a-zA-Z", "blank": " \\t", "cntrl": "\\x00-\\x1f\\x7f", "digit": "0-9",
    "graph": "\\x21-\\x7e", "lower": "a-z", "print": "\\x20-\\x7e", "punct": "!-/:-@\\[-`{-~",
    "space": " \\t\\n\\r\\f\\v", "upper": "A-Z", "xdigit": "0-9A-Fa-f"
}
_SENSITIVE_RULES = (
    ".env", ".env.*", "!.env.example", "!.env.sample", "!.env.template", "*.pem", "*.key", "*.p12", "*.pfx",
    "*.jks", "*.keystore", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "*.kdbx", ".netrc", ".pypirc",
    "_my_config.py", "*.db", "*.sqlite", "*.sqlite3"
)
_PRIVATE_KEY = re.compile(rb"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")
_SERVICE_ACCOUNT = (b'"private_key"', b'"client_email"')


def _is_junk(rel):
    segments = rel.split("/")
    name = segments[-1]
    lower = name.lower()
    for segment in segments[:-1]:
        if segment in _JUNK_DIRS or segment.endswith(".egg-info"):
            return True
    if name in _JUNK_DIRS: return True
    if lower in _JUNK_FILES: return True
    return any(lower.endswith(suffix) for suffix in _JUNK_SUFFIXES)


def _bracket(pattern, start):
    i, items = start + 1, ""
    negate = i < len(pattern) and pattern[i] in "!^"
    if negate: i += 1
    first = True
    while i < len(pattern):
        char = pattern[i]
        if char == "]" and not first:
            if not items: return None
            return ("[^/" + items + "]" if negate else "(?!/)[" + items + "]"), i + 1
        first = False
        if char == "[" and pattern.startswith("[:", i):
            end = pattern.find(":]", i + 2)
            if end != -1 and pattern[i + 2:end] in _CLASSES:
                items += _CLASSES[pattern[i + 2:end]]
                i = end + 2
                continue
        if char == "\\" and i + 1 < len(pattern):
            i += 1
            char = pattern[i]
        if i + 2 < len(pattern) and pattern[i + 1] == "-" and pattern[i + 2] != "]":
            end = pattern[i + 3] if pattern[i + 2] == "\\" and i + 3 < len(pattern) else pattern[i + 2]
            if ord(end) >= ord(char): items += re.escape(char) + "-" + re.escape(end)
            i += 4 if pattern[i + 2] == "\\" else 3
            continue
        items += re.escape(char)
        i += 1
    return None


def _translate(pattern):
    out, i, length = "", 0, len(pattern)
    while i < length:
        char = pattern[i]
        if char == "*":
            j = i
            while j < length and pattern[j] == "*": j += 1
            leading = i == 0 or pattern[i - 1] == "/"
            trailing = j == length or pattern[j] == "/"
            if j - i >= 2 and leading and trailing:
                out += ".*" if j == length else "(?:.*/)?"
                i = j if j == length else j + 1
            else:
                out += "[^/]*"
                i = j
            continue
        if char == "?": out += "[^/]"
        elif char == "[":
            parsed = _bracket(pattern, i)
            if parsed is not None:
                out += parsed[0]
                i = parsed[1]
                continue
            out += "\\["
        elif char == "\\" and i + 1 < length:
            i += 1
            out += re.escape(pattern[i])
        else: out += re.escape(char)
        i += 1
    return out


def _trim(line):
    end = len(line)
    while end and line[end - 1] == " " and not (end > 1 and line[end - 2] == "\\"): end -= 1
    return line[:end]


def parse_rule(raw):
    line = _trim(raw.rstrip("\r"))
    if not line or line.startswith("#"): return None

    negate = line.startswith("!")
    if negate: line = line[1:]

    dir_only = line.endswith("/") and not line.endswith("\\/")
    if dir_only: line = line.rstrip("/")

    anchored = line.startswith("/")
    if anchored: line = line[1:]
    path_mode = anchored or "/" in line

    if not line: return None
    return negate, dir_only, path_mode, re.compile("^" + _translate(line) + "$", re.DOTALL)


def parse_rules(text):
    return [rule for rule in (parse_rule(raw) for raw in text.split("\n")) if rule]


def _collect_ignores(root, rels):
    ignores = []
    for rel in rels:
        if rel != _IGNORE_NAME and not rel.endswith("/" + _IGNORE_NAME):
            continue
        base = rel[:-len(_IGNORE_NAME)].rstrip("/")
        ignores.append((base, parse_rules((root / rel).read_text(encoding="utf-8", errors="ignore"))))
    ignores.sort(key=lambda ig: 0 if ig[0] == "" else len(ig[0].split("/")))
    return ignores


def _excluded(path, is_dir, ignores):
    result = None
    for base, rules in ignores:
        if base and not path.startswith(base + "/"): continue
        local = path[len(base) + 1:] if base else path
        name = local.rsplit("/", 1)[-1]
        for negate, dir_only, path_mode, regex in rules:
            if dir_only and not is_dir: continue
            if regex.match(local if path_mode else name): result = not negate
    return bool(result)


def is_ignored(rel, ignores):
    segments = rel.split("/")
    for depth in range(1, len(segments)):
        if _excluded("/".join(segments[:depth]), True, ignores): return True
    return _excluded(rel, False, ignores)


def _sensitive_content(path):
    try:
        if path.stat().st_size > SNIFF_LIMIT: return False
        data = path.read_bytes()
    except OSError:
        return False
    return bool(_PRIVATE_KEY.search(data)) or all(marker in data for marker in _SERVICE_ACCOUNT)


def _walk(root):
    files, links = [], []
    for current, folders, names in os.walk(root, followlinks=False):
        base = Path(current)
        kept = []
        for name in folders:
            rel = (base / name).relative_to(root).as_posix()
            if (base / name).is_symlink(): links.append(rel)
            else: kept.append(name)
        folders[:] = kept
        for name in names:
            path = base / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink(): links.append(rel)
            elif stat.S_ISREG(path.lstat().st_mode): files.append(rel)
    return files, links


def scan(root):
    root = Path(root)
    rels, links = _walk(root)
    ignores = _collect_ignores(root, rels)
    sensitive_rules = [("", parse_rules("\n".join(_SENSITIVE_RULES)))]
    selected, sensitive = [], []
    for rel in sorted(rels):
        if _is_junk(rel) or is_ignored(rel, ignores): continue
        if is_ignored(rel, sensitive_rules) or _sensitive_content(root / rel): sensitive.append(rel)
        else: selected.append(rel)
    links = sorted(rel for rel in links if not _is_junk(rel) and not is_ignored(rel, ignores))
    return selected, sensitive, links


def _pack(entries):
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


def selected_files(root):
    return scan(root)[0]


def build_archive(root, files=None):
    root = Path(root)
    entries = [
        (rel, (root / rel).read_bytes())
        for rel in (selected_files(root) if files is None else files)
    ]
    return _pack(entries)


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()
