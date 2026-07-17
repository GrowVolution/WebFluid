

def match_version(meta, constraint):
    from webfluid.core.additive.version import Version
    from webfluid.utils.core import check_required_version

    matching = []
    for release in meta.get("releases", []):
        version = release["version"]
        try:
            candidate = Version(*version.split("."))
            if candidate.stage != "": continue
            if constraint != "*" and not check_required_version(
                    constraint, "additive", candidate
            ): continue
            matching.append((tuple(candidate), version))
        except (ValueError, TypeError): continue

    if not matching: return None
    matching.sort()
    return matching[-1][1]
