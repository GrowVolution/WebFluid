
_stage_map = {
    "a": 0,
    "b": 1,
    "rc": 2
}


def final_version(v_str):
    if "a" in v_str:
        stage = "a"
        v, build = map(int, v_str.split("a"))
    elif "b" in v_str:
        stage = "b"
        v, build = map(int, v_str.split("b"))
    elif "rc" in v_str:
        stage = "rc"
        v, build = map(int, v_str.split("rc"))
    else:
        stage = ""
        v, build = int(v_str), 0

    return v, stage, build


def check_required_version(requirement, version_type="wf", additive_version=None):
    version_type = version_type.lower()
    if version_type not in ["wf", "additive"]:
        raise ValueError("Invalid version type.")

    if version_type == "additive" and additive_version is None:
        raise RuntimeError("Cannot check with unknown additive version.")

    from webfluid import FluidVersion, AdditiveVersion, version
    ver_cls = FluidVersion if version_type == "wf" else AdditiveVersion

    if requirement != "*":
        for candidate in (">=", "<=", "==", ">", "<"):
            if requirement.startswith(candidate):
                op = candidate
                ver = requirement[len(candidate):].strip()
                break
        else:
            raise ValueError(f"Invalid version operator in requirement '{requirement}'.")
    else:
        return True

    if version_type == "additive":
        current = additive_version if isinstance(additive_version, ver_cls) \
            else ver_cls(*additive_version.split("."))
    else:
        current = version()

    try: target = ver_cls(*ver.split("."))
    except ValueError:
        raise ValueError("Invalid requirement string.")

    current_stage = _stage_map.get(current.stage, 3)
    target_stage = _stage_map.get(target.stage, 3)

    return {
        ">":  current > target and (current_stage > target_stage or current.build > target.build),
        ">=": current >= target and (current_stage >= target_stage or current.build >= target.build),
        "<":  current < target and (current_stage < target_stage or current.build < target.build),
        "<=": current <= target and (current_stage <= target_stage or current.build <= target.build),
        "==": current == target and (current_stage == target_stage or current.build == target.build),
    }.get(op, False)
