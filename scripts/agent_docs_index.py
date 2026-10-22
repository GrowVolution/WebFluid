from pathlib import Path
import sys

from webfluid.utils.agents import discover, index

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "src" / "webfluid" / ".agents"


def main():
    for path in discover(AGENTS.parent):
        state = "updated" if index(path) else "current"
        print(f"{path.relative_to(ROOT).as_posix()}: {state}")


if __name__ == "__main__": sys.exit(main())
