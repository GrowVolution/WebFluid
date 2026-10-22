from webfluid.utils.agents import CLOSE, OPEN, discover, index

CONTRACT = "# Thing — Contract\n\n# API\n\n## GET /a\n\nAnswers a.\n\n## GET /b\n\nAnswers b.\n\n# Events\n\nNone.\n"
SKILL = (
    "---\nname: thing\n---\n\n# Using thing\n\n## Rules\n\nKeep it small.\n\n## Contract map\n\n"
    "<!-- index ../CONTRACT.md -->\n<!-- /index -->\n\n```markdown\n<!-- index ../MISSING.md -->\n<!-- /index -->\n```\n"
)


def _package(tmp_path):
    (tmp_path / ".agents").mkdir()
    contract = tmp_path / "CONTRACT.md"
    skill = tmp_path / ".agents" / "SKILL.md"
    contract.write_bytes(CONTRACT.encode())
    skill.write_bytes(SKILL.replace("\n", "\r\n").encode())
    return contract, skill


def test_discovery_puts_contracts_first_and_skips_build_trees(tmp_path):
    contract, skill = _package(tmp_path)
    (tmp_path / "node_modules" / ".agents").mkdir(parents=True)
    (tmp_path / "node_modules" / ".agents" / "SKILL.md").write_text("# x\n")

    assert discover(tmp_path) == [contract, skill]


def test_indexes_settle_and_a_second_run_changes_nothing(tmp_path):
    contract, skill = _package(tmp_path)

    assert index(contract) is True
    assert index(skill) is True
    assert index(contract) is False and index(skill) is False

    lines = contract.read_text(encoding="utf-8").split("\n")
    assert lines[2] == OPEN and CLOSE in lines
    entry = next(line for line in lines if "**API**" in line)
    start, end = map(int, entry.split("`")[1].split("-"))
    assert lines[start - 1] == "# API" and lines[end] == "# Events"


def test_a_linked_block_carries_the_ranges_of_its_target_and_keeps_line_endings(tmp_path):
    contract, skill = _package(tmp_path)
    index(skill)

    raw = skill.read_bytes()
    assert b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"")
    text = raw.decode().replace("\r\n", "\n")
    linked = text.split("<!-- index ../CONTRACT.md -->")[1].split(CLOSE)[0]
    assert "**API**" in linked and "GET /b" in linked
    assert "<!-- index ../MISSING.md -->\n<!-- /index -->" in text


def test_check_mode_reports_a_stale_index_without_writing(tmp_path):
    contract, skill = _package(tmp_path)
    before = contract.read_bytes()

    assert index(contract, write=False) is True
    assert contract.read_bytes() == before
