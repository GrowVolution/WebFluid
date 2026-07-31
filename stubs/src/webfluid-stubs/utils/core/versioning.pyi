from webfluid import AdditiveVersion

_stage_map: dict[str, int]

def final_version(v_str: str) -> tuple[int, str, int]: ...
def check_required_version(
    requirement: str, version_type: str = "wf",
    additive_version: AdditiveVersion | str | None = None
) -> bool: ...
