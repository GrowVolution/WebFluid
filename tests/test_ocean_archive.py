from pathlib import Path
import io, os, shutil, subprocess, tarfile

import pytest

from webfluid.cli.ocean.archive import _collect_ignores, build_archive, is_ignored, scan

ROOT_RULES = """# a comment
*.log
!keep.log
/build/
dist
docs/**/*.tmp
**/cache
a/**/b
abc/**
[Bb]in/
*.[oa]
\\#hash.txt
\\!bang.txt
trailing.txt
foo/*
!foo/keep/
nested/deep
x?y.txt
[!z]only.txt
**/temp/
[folders]
.idea/
[files]
_my_config.py
"""

FLUTTER_RULES = """build/
.dart_tool/
!build/keep.txt
*.g.dart
!important.g.dart
"""

NESTED_RULES = """*.txt
!keep.txt
/local.cfg
"""

FILES = [
    "app.log", "keep.log", "sub/app.log", "build/out.js", "src/build/out.js", "dist/a.js", "src/dist",
    "docs/a/b/x.tmp", "docs/x.tmp", "other/x.tmp", "cache/x", "src/cache/y", "a/b", "a/x/b", "a/x/y/b", "a/xb",
    "abc/one", "abc/two/three", "abcd/one", "Bin/x", "bin/y", "bins/z", "lib.o", "lib.a", "lib.c", "#hash.txt",
    "!bang.txt", "trailing.txt", "foo/drop.txt", "foo/keep/kept.txt", "nested/deep", "nested/deeper",
    "nested/notes.txt", "nested/keep.txt", "nested/local.cfg", "nested/inner/local.cfg", "nested/inner/x.txt",
    "xay.txt", "xy.txt", "aonly.txt", "zonly.txt", "src/temp/t", "temp", "f", "s", "x", "README.md",
    "_my_config.py", "pkg/_my_config.py", ".idea/workspace.xml",
    "flutter_sdk/lib/main.dart", "flutter_sdk/lib/model.g.dart", "flutter_sdk/lib/important.g.dart",
    "flutter_sdk/build/app.apk", "flutter_sdk/build/keep.txt", "flutter_sdk/.dart_tool/cache",
    "flutter_sdk/example/build/x", "flutter_sdk/pubspec.yaml"
]


def _tree(root: Path):
    (root / ".gitignore").write_text(ROOT_RULES, encoding="utf-8")
    (root / "flutter_sdk").mkdir()
    (root / "flutter_sdk" / ".gitignore").write_text(FLUTTER_RULES, encoding="utf-8")
    (root / "nested").mkdir()
    (root / "nested" / ".gitignore").write_text(NESTED_RULES, encoding="utf-8")
    for rel in FILES:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rel, encoding="utf-8")


def _git_selection(root: Path) -> set[str]:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    result = subprocess.run(
        ["git", "-c", "core.excludesFile=" + str(root / "none"), "-c", "core.ignorecase=false",
         "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=root, check=True, capture_output=True
    )
    shutil.rmtree(root / ".git", ignore_errors=True)
    return {name for name in result.stdout.decode("utf-8").split("\0") if name}


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_ignore_rules_match_git_exactly(tmp_path):
    _tree(tmp_path)
    expected = _git_selection(tmp_path)
    rels = [path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file()]
    ignores = _collect_ignores(tmp_path, rels)
    actual = {rel for rel in rels if not is_ignored(rel, ignores)}
    assert actual == expected, {"only ours": sorted(actual - expected), "only git": sorted(expected - actual)}


def test_known_ignore_semantics(tmp_path):
    _tree(tmp_path)
    rels = [path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*") if path.is_file()]
    ignores = _collect_ignores(tmp_path, rels)
    kept = {rel for rel in rels if not is_ignored(rel, ignores)}
    assert {"a/xb", "keep.log", "foo/keep/kept.txt", "nested/keep.txt", "nested/inner/local.cfg",
            "flutter_sdk/lib/important.g.dart", "abcd/one"} <= kept
    assert not {"a/b", "a/x/y/b", "flutter_sdk/build/keep.txt", "flutter_sdk/example/build/x",
                "flutter_sdk/lib/model.g.dart", "nested/local.cfg", "docs/a/b/x.tmp", "src/cache/y",
                "trailing.txt", "foo/drop.txt", "Bin/x", "#hash.txt", "!bang.txt"} & kept


def test_scan_leaves_out_secrets_and_links(tmp_path):
    (tmp_path / "manifest.json").write_text("{}")
    (tmp_path / ".env").write_text("TOKEN=1")
    (tmp_path / ".env.example").write_text("TOKEN=")
    (tmp_path / "service.json").write_text('{"type": "service_account", "private_key": "x", "client_email": "y"}')
    (tmp_path / "notes.txt").write_text("-----BEGIN " + "OPENSSH PRIVATE KEY-----\nabc\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("")
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / "secret.ini").write_text("SECRET")
    linked = True
    try: os.symlink(outside / "secret.ini", tmp_path / "linked.ini")
    except (OSError, NotImplementedError): linked = False

    selected, sensitive, links = scan(tmp_path)
    assert selected == [".env.example", "manifest.json"]
    assert sensitive == [".env", "notes.txt", "service.json"]
    assert links == (["linked.ini"] if linked else [])
    with tarfile.open(fileobj=io.BytesIO(build_archive(tmp_path, selected))) as archive:
        assert sorted(archive.getnames()) == [".env.example", "manifest.json"]
