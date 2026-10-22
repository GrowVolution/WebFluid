from pathlib import Path
import sys
import tarfile
import zipfile


REQUIRED = (
    "CONTRACT.md",
    ".agents/SKILL.md",
    ".agents/references/additives.md",
)


def check(path):
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
        prefix = "webfluid/"
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path) as archive:
            names = archive.getnames()
        prefix = f"{path.name.removesuffix('.tar.gz')}/src/webfluid/"
    else:
        raise ValueError(f"Unsupported distribution: {path}")

    missing = [prefix + name for name in REQUIRED if prefix + name not in names]
    unwanted = [name for name in names if (
        "/surface/dist/" in name or "/__pycache__/" in name
        or name.endswith((".pyc", ".pyo"))
    )]
    if missing or unwanted:
        raise ValueError(f"{path.name}: missing documentation={missing}; cache files={unwanted}")
    print(f"{path.name}: documentation present; no toolchain cache or bytecode")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/check_distribution.py <distribution-directory>")
    directory = Path(sys.argv[1])
    artifacts = sorted([*directory.glob("*.whl"), *directory.glob("*.tar.gz")])
    if not artifacts:
        raise SystemExit(f"No distributions found in {directory}")
    for artifact in artifacts:
        check(artifact)


if __name__ == "__main__":
    main()
