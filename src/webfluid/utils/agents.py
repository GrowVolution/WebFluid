from pathlib import Path
import re, textwrap

OPEN = "<!-- index -->"
CLOSE = "<!-- /index -->"
LINKED = re.compile(r"^<!-- index (\S+) -->$")

LEAD = (
    "Read this file in parts. Each range is `first-last` as the file stands now — open one with "
    "the Read tool's `offset`/`limit`, or `sed -n 'first,lastp'`."
)
SKILL_LEAD = (
    "This file is short enough to read whole; the ranges are for coming back to one section. Every "
    "file it points to opens with an index of the same shape — read those first 30 lines, then only "
    "the ranges the task needs."
)
LINKED_LEAD = "Sections of `{target}`, as that file stands now:"

SKIPPED = frozenset({".git", "node_modules", "build", ".dart_tool", "__pycache__", ".venv", "dist"})

__all__ = ["OPEN", "CLOSE", "LEAD", "SKILL_LEAD", "discover", "index"]


def _strip(lines):
    if OPEN not in lines: return list(lines)

    head = lines[:lines.index(OPEN)]
    rest = lines[lines.index(CLOSE) + 1:]

    while head and not head[-1].strip(): head.pop()
    while rest and not rest[0].strip(): rest.pop(0)
    return head + [""] + rest


def _headings(lines):
    found, fenced = [], False

    for number, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced: continue

        match = re.match(r"^(#{1,3}) (.+?)\s*$", line)
        if match: found.append((len(match.group(1)), match.group(2), number))

    return found


def _entries(found, total):
    if found and found[0][0] == 1: found = found[1:]

    entries = []
    for position, (level, title, start) in enumerate(found):
        end = total
        for other, _, line in found[position + 1:]:
            if other <= level:
                end = line - 1
                break
        entries.append((level, title, start, end))

    lines, stack = [], []
    for level, title, start, end in entries:
        while stack and stack[-1] >= level: stack.pop()

        depth = len(stack)
        stack.append(level)

        name = f"**{title}**" if not depth else title
        lines.append(f"{'  ' * depth}- `{start}-{end}` {name}")
    return lines


def _total(lines):
    return len(lines) - 1 if lines and not lines[-1] else len(lines)


def _render(found, total, lead):
    lines = _entries(found, total)
    if not lines: return []
    return [OPEN, *textwrap.wrap(lead, 100), "", *lines, CLOSE]


def _insert(lines, block):
    if not block: return list(lines)

    for number, line in enumerate(lines):
        if line.startswith("# "):
            return lines[:number + 1] + ["", *block] + lines[number + 1:]

    return ["", *block, *lines]


def _linked(lines, origin, write, seen):
    result, position, fenced = [], 0, False

    while position < len(lines):
        line = lines[position]
        if line.lstrip().startswith("```"): fenced = not fenced
        match = None if fenced else LINKED.match(line)
        target = (origin.parent / match.group(1)).resolve() if match else None
        if target is None or not target.is_file():
            result.append(line)
            position += 1
            continue

        end = position + 1
        while end < len(lines) and lines[end] != CLOSE: end += 1

        if target not in seen: index(target, write=write, seen=seen | {origin.resolve()})
        content = target.read_text(encoding="utf-8").split("\n")
        rendered = _entries(_headings(content), _total(content))

        result += [lines[position], LINKED_LEAD.format(target=match.group(1)), "", *rendered, CLOSE]
        position = end + 1

    return result


def index(path, lead=None, write=True, seen=frozenset()):
    path = Path(path)
    if lead is None: lead = SKILL_LEAD if path.name == "SKILL.md" else LEAD

    raw = path.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    original = raw.replace("\r\n", "\n")
    lines = _linked(_strip(original.split("\n")), path, write, seen)
    block = []

    for _ in range(10):
        candidate = _insert(lines, block)
        current = _render(_headings(candidate), _total(candidate), lead)

        if current == block:
            text = "\n".join(candidate)
            if text == original: return False
            if write: path.write_bytes(text.replace("\n", newline).encode("utf-8"))
            return True

        block = current

    raise RuntimeError(f"The index of {path.name} did not settle.")


def discover(root):
    root = Path(root)
    found = []

    for path in root.rglob("*.md"):
        parts = path.relative_to(root).parts
        if SKIPPED.intersection(parts): continue
        if path.name == "CONTRACT.md" or ".agents" in parts: found.append(path)

    return sorted(found, key=lambda path: (path.name != "CONTRACT.md", path.as_posix()))
