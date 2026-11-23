import hashlib, json

import pytest

from webfluid.utils.integrity import IntegrityReference, Artifact

GENERATOR = """from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parent
artifacts = {}
for name, binary in (("text", False), ("blob", True)):
    data = (ROOT / name / "v1.bin").read_bytes()
    digest = hashlib.sha256(data if binary else data.replace(b"\\r\\n", b"\\n")).hexdigest()
    artifacts[f"t_{name}"] = {"latest": "v1", "versions": [{"version": "v1", "file": f"{name}/v1.bin",
                                                            "sha256": digest, "size": len(data)}]}
(ROOT / "manifest.json").write_text(json.dumps({"format": 2, "algorithm": "sha256", "artifacts": artifacts}))
"""
TEXT = b"export const a = 1\r\n"
BLOB = b"\x00asm\r\n\x01"


@pytest.fixture
def reference(tmp_path):
    from git import Repo
    source = tmp_path / "reference"
    for name, data in (("text", TEXT), ("blob", BLOB)):
        (source / name).mkdir(parents=True)
        (source / name / "v1.bin").write_bytes(data)
    (source / "generate.py").write_text(GENERATOR, encoding="utf-8")
    repo = Repo.init(source)
    repo.index.add(["generate.py", "text/v1.bin", "blob/v1.bin"])
    repo.index.commit("reference")

    served = tmp_path / "served"
    served.mkdir()
    (served / "a.js").write_bytes(TEXT.replace(b"\r\n", b"\n"))
    (served / "core.wasm").write_bytes(BLOB)

    class Reference(IntegrityReference):
        pass

    Reference.setup("thing", "https://github.com/example/thing-integrity", "reference", [
        Artifact("t_text", served / "a.js", "/thing/static/a.js", "Text"),
        Artifact("t_blob", served / "core.wasm", "/thing/static/core.wasm", "Blob", kind="wasm", binary=True)
    ], tmp_path, update=False, timeout=20)
    return Reference, served


def _by_id(records):
    return { record["id"]: record for record in records }


async def test_records_match_and_binary_artifacts_are_hashed_raw(reference):
    Reference, _ = reference
    records = _by_id(await Reference.provide({ "run": "one" }))
    for record in records.values():
        assert record["provenance"]["status"] == "reference-match" and record["served_version"] == "v1"
        assert record["reference"]["hash"] == record["hash"] and record["additive"] == "thing"
    assert records["t_blob"]["hash"] == hashlib.sha256(BLOB).hexdigest() and records["t_blob"]["type"] == "wasm"
    assert records["t_text"]["reference"]["manifest"] == \
        "https://raw.githubusercontent.com/example/thing-integrity/main/manifest.json"
    assert Reference.served_versions() == { "t_text": "v1", "t_blob": "v1" }
    assert (await Reference.status())["reference"] == "ok"


async def test_changed_file_is_a_mismatch_and_a_run_is_computed_once(reference):
    Reference, served = reference
    first = await Reference.compute("same")
    (served / "a.js").write_bytes(b"export const a = 2\n")
    assert await Reference.compute("same") is first
    records = _by_id(await Reference.provide({ "run": "changed" }))
    assert records["t_text"]["provenance"]["status"] == "reference-mismatch"
    assert records["t_text"]["version"] == "unknown" and records["t_blob"]["provenance"]["status"] == "reference-match"


async def test_forged_manifest_is_not_reproducible(reference, tmp_path):
    Reference, _ = reference
    generator = tmp_path / "reference" / "generate.py"
    generator.write_text(GENERATOR.replace('"sha256": digest', '"sha256": "0" * 64'), encoding="utf-8")
    records = await Reference.provide({ "run": "forged" })
    assert all(record["provenance"]["status"] == "reference-unavailable" for record in records)
    assert records[0]["context"]["error"] == "NOT_REPRODUCIBLE"
    manifest = json.loads((tmp_path / "reference" / "manifest.json").read_text())
    assert manifest["artifacts"]["t_text"]["versions"][0]["sha256"] == "0" * 64


async def test_empty_repository_is_unconfigured(reference, monkeypatch):
    Reference, _ = reference
    monkeypatch.setattr(Reference, "repository", "")
    records = await Reference.provide({ "run": "unconfigured" })
    assert {record["context"]["error"] for record in records} == {"REFERENCE_UNCONFIGURED"}
    assert records[0]["reference"]["url"] is None and records[0]["reference"]["manifest"] is None


def test_refresh_closes_every_repository_it_opens(reference, monkeypatch):
    import gc
    from git import Repo
    Reference, _ = reference
    opened, closed = [], []
    init, close = Repo.__init__, Repo.close

    def tracked_init(self, *args, **kwargs):
        opened.append(id(self))
        init(self, *args, **kwargs)

    def tracked_close(self):
        closed.append(id(self))
        close(self)

    monkeypatch.setattr(Repo, "__init__", tracked_init)
    monkeypatch.setattr(Repo, "close", tracked_close)
    gc.disable()
    try: state = Reference.refresh()
    finally: gc.enable()
    assert state["commit"] and opened and set(opened) <= set(closed)
