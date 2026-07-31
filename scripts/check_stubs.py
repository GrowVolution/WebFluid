from pathlib import Path
import ast, sys

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "src" / "webfluid"
STUBS = ROOT / "stubs" / "src" / "webfluid-stubs"

SKIP = ("surface/dist", "__pycache__", "extensions/migrate/templates")


def modules(root, suffix):
    found = {}
    for path in root.rglob(f"*{suffix}"):
        relative = path.relative_to(root).as_posix()
        if any(part in relative for part in SKIP): continue
        found[relative.removesuffix(suffix)] = path
    return found


def symbols(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"): names.add(node.name)

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    names.add(target.id)

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and not node.target.id.startswith("_"):
                names.add(node.target.id)

        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                if not name.startswith("_"): names.add(name)

    return names


def declared_all(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign): continue
        for target in node.targets:
            if not isinstance(target, ast.Name) or target.id != "__all__":
                continue
            if not isinstance(node.value, (ast.List, ast.Tuple)): return None
            return {
                e.value for e in node.value.elts if isinstance(e, ast.Constant)
            }
    return None


def main():
    runtime = modules(RUNTIME, ".py")
    stubs = modules(STUBS, ".pyi")

    problems = []

    for name in sorted(set(runtime) - set(stubs)):
        problems.append(f"missing stub:  {name}.pyi")
    for name in sorted(set(stubs) - set(runtime)):
        problems.append(f"orphaned stub: {name}.pyi")

    for name in sorted(set(runtime) & set(stubs)):
        exported = declared_all(runtime[name])
        if exported is None: continue

        missing = exported - symbols(stubs[name])
        for symbol in sorted(missing):
            problems.append(f"unstubbed export: {name}.{symbol}")

    for problem in problems: print(problem)

    if problems:
        print(f"\n{len(problems)} problem(s)")
        return 1

    print(f"stub tree mirrors {len(runtime)} runtime modules")
    return 0


if __name__ == "__main__":
    sys.exit(main())
