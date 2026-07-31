

def id_check(additive_id):
    from ..core import safe_string
    safe_id = safe_string(additive_id)
    if additive_id != safe_id:
        return False, f"Invalid id format '{additive_id}'. Try '{safe_id}' for example."
    return True, additive_id


def version_check(v):
    version_str = v.lower().strip()
    if not version_str:
        return False, "Additive version not defined."

    first_char_invalid = not version_str[0].isdigit()

    if  first_char_invalid:
        return False, "Invalid version string format."

    v_numbers = version_str.split(" ")[0].split(".")
    if len(v_numbers) > 3:
        return False, "Too many version numbers."

    for v_number in v_numbers:
        if not v_number.isdigit() and \
                v_numbers.index(v_number) != len(v_numbers) - 1:
            return False, "Invalid version number format."
        elif not v_number.isdigit():
            if not (
                    "a" in v_number and len(v_number.split("a")) == 2 or
                    "b" in v_number and len(v_number.split("b")) == 2 or
                    "rc" in v_number and len(v_number.split("rc")) == 2
            ): return False, "Invalid version number format."

        if v_number.isdigit():
            v = int(v_number)
            if v < 0 or v > 999:
                return False, "Version number cannot be negative or greater than 999."

        else:
            from ..core import final_version
            v, _, b = final_version(v_number)
            if v < 0 or v > 999:
                return False, "Version number cannot be negative or greater than 999."
            if b < 1 or b > 9:
                return False, "Build number cannot smaller than 1 or greater than 9."

    return True, version_str


def type_check(t):
    if t not in ("base", "default"):
        return False, f"Invalid type string '{t}'."
    return True, t
