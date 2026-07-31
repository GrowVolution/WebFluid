

def id_check(additive_id):
    from ..core import safe_string
    safe_id = safe_string(additive_id)
    if additive_id != safe_id:
        return False, f"Invalid id format '{additive_id}'. Try '{safe_id}' for example."
    return True, additive_id


def version_check(v):
    from packaging.version import InvalidVersion, Version

    version_str = v.lower().strip()
    if not version_str:
        return False, "Additive version not defined."

    try: version = Version(version_str)
    except InvalidVersion:
        return False, "Invalid version string format."

    if version.epoch or version.dev is not None \
            or version.post is not None or version.local:
        return False, "Epoch, development, post and local versions are not supported."

    if len(version.release) > 3:
        return False, "Too many version numbers."

    if any(number > 999 for number in version.release):
        return False, "Version number cannot be negative or greater than 999."

    if version.pre is not None:
        stage, build = version.pre
        if stage not in ("a", "b", "rc"):
            return False, "Invalid version number format."
        if build < 1 or build > 9:
            return False, "Build number cannot smaller than 1 or greater than 9."

    return True, str(version)


def type_check(t):
    if t not in ("base", "default"):
        return False, f"Invalid type string '{t}'."
    return True, t
