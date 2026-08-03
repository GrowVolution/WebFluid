from pathlib import Path
import re, tomllib, pytest

from webfluid.utils.additives import version_check
from webfluid.utils.core import Version, check_required_version

ROOT = Path(__file__).resolve().parents[1]


def check(requirement, version):
    return check_required_version(requirement, "additive", version)


def declared(path):
    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_every_release_artifact_carries_the_same_version():
    runtime = declared(ROOT / "pyproject.toml")
    stubs = declared(ROOT / "stubs" / "pyproject.toml")
    version = runtime["project"]["version"]

    assert stubs["project"]["version"] == version
    assert f"webfluid=={version}" in stubs["project"]["dependencies"]
    assert f"webfluid-stubs=={version}" in \
           runtime["project"]["optional-dependencies"]["typing"]
    assert re.search(
        rf"WEBFLUID_VERSION={re.escape(version)}\b",
        (ROOT / "Dockerfile").read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("requirement, version, expected", [
    (">1.0.0a1", "1.0.0a2", True),
    (">1.0.0a1", "1.0.0b1", True),
    (">1.0.0a2", "1.0.0a1", False),
    (">=1.0.0a1", "1.0.0b1", True),
    (">=1.0.0b1", "1.0.0a1", False),
    ("==1.0.0a1", "1.0.0b1", False),
    ("==1.0.0a1", "1.0.0a1", True),
    ("<1.0.0", "0.9.9", True),
    ("<1.0.0", "1.0.0rc1", False),
    (">=1.1.0", "1.2.0", True),
    (">=1.0.0a1", "1.0.0", True),
    ("*", "0.0.1a1", True),
    (">=1.0,<2.0", "1.5.0", True),
    (">=1.0,<2.0", "2.0.0", False)
])
def test_requirements_resolve_correctly(requirement, version, expected):
    assert check(requirement, version) is expected


def test_stage_ordering():
    assert Version("1.0.0a1") < Version("1.0.0a2") < Version("1.0.0b1")
    assert Version("1.0.0b1") < Version("1.0.0rc1") < Version("1.0.0")


def test_stage_and_build_are_exposed():
    version = Version("1.0.0b3")
    assert version.stage == "b"
    assert version.build == 3

    stable = Version("1.0.0")
    assert stable.stage == ""
    assert stable.build == 0


def test_version_accepts_split_parts():
    assert str(Version("1", "0", "0b1")) == "1.0.0b1"


def test_invalid_requirement_raises():
    with pytest.raises(ValueError): check("~~1.0", "1.0.0")


def test_invalid_version_raises():
    with pytest.raises(ValueError): Version("not-a-version")


@pytest.mark.parametrize("version, valid", [
    ("1.0.0", True),
    ("1.0.0b1", True),
    ("1.0", True),
    ("1.0.0.1", False),
    ("1000.0.0", False),
    ("1.0.0b0", False),
    ("1.0.0.dev1", False),
    ("", False)
])
def test_manifest_version_check(version, valid):
    assert version_check(version)[0] is valid
