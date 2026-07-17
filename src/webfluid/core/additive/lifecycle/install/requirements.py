

def _normalize_requirements(requirement):
    if isinstance(requirement, list):
        normalized = {}
        for entry in requirement:
            if not isinstance(entry, str): continue
            parts = entry.split("@")
            normalized[parts[0]] = parts[1] if len(parts) == 2 else "*"
        return normalized
    return requirement if isinstance(requirement, dict) else {}


def required_additives(additive):
    if "requires" not in additive.manifest: return {}
    return _normalize_requirements(
        additive.manifest["requires"].get("additives") or {}
    )
