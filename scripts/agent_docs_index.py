from pathlib import Path
import re, sys, textwrap

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "src" / "webfluid" / ".agents" / "skills" / "webfluid"

OPEN = "<!-- index -->"
CLOSE = "<!-- /index -->"

LEAD = (
    "Read this file in parts. Each range is `first-last` as the file stands now — open one with "
    "the Read tool's `offset`/`limit`, or `sed -n 'first,lastp'`."
)

SKILL_LEAD = (
    "This file is short enough to read whole; the ranges are for coming back to one section. Every "
    "`references/*.md` opens with an index of the same shape — read those first 30 lines, then only "
    "the ranges the task needs."
)


def strip_index(lines):
    if OPEN not in lines: return list(lines)

    head = lines[:lines.index(OPEN)]
    rest = lines[lines.index(CLOSE) + 1:]

    while head and not head[-1].strip(): head.pop()
    while rest and not rest[0].strip(): rest.pop(0)
    return head + [""] + rest


def headings(lines):
    found, fenced = [], False

    for number, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced: continue

        match = re.match(r"^(#{1,3}) (.+?)\s*$", line)
        if match: found.append((len(match.group(1)), match.group(2), number))

    return found


def render(found, total, lead):
    if found and found[0][0] == 1: found = found[1:]
    if not found: return []

    entries = []
    for index, (level, title, start) in enumerate(found):
        end = total
        for other, _, line in found[index + 1:]:
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

    return [OPEN, *textwrap.wrap(lead, 100), "", *lines, CLOSE]


def insert(lines, block):
    if not block: return list(lines)

    for number, line in enumerate(lines):
        if line.startswith("# "):
            return lines[:number + 1] + ["", *block] + lines[number + 1:]

    return ["", *block, *lines]


def build(path, lead):
    lines = strip_index(path.read_text(encoding="utf-8").split("\n"))
    block = []

    for _ in range(10):
        candidate = insert(lines, block)
        total = len(candidate) - 1 if candidate and not candidate[-1] else len(candidate)
        current = render(headings(candidate), total, lead)

        if current == block:
            path.write_text("\n".join(candidate), encoding="utf-8")
            return len(block)

        block = current

    raise RuntimeError(f"index for {path.name} did not settle")


def main():
    targets = [(SKILL / "SKILL.md", SKILL_LEAD)]
    targets += [(path, LEAD) for path in sorted((SKILL / "references").glob("*.md"))]

    for path, lead in targets:
        print(f"{path.relative_to(ROOT).as_posix()}: {build(path, lead)} lines")


if __name__ == "__main__": sys.exit(main())
