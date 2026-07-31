from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version as _Version


class Version(_Version):
    def __init__(self, *parts):
        if not parts: raise ValueError("Invalid version format.")

        v_str = ".".join(str(part) for part in parts)
        try: super().__init__(v_str)
        except InvalidVersion:
            raise ValueError(f"Invalid version format '{v_str}'.")

    @property
    def stage(self): return self.pre[0] if self.pre else ""

    @property
    def build(self): return self.pre[1] if self.pre else 0


def check_required_version(requirement, version_type="wf", additive_version=None):
    version_type = version_type.lower()
    if version_type not in ("wf", "additive"):
        raise ValueError("Invalid version type.")

    if version_type == "additive" and additive_version is None:
        raise RuntimeError("Cannot check with unknown additive version.")

    if requirement == "*": return True

    try: specifier = SpecifierSet(requirement, prereleases=True)
    except InvalidSpecifier:
        raise ValueError(f"Invalid requirement string '{requirement}'.")

    if version_type == "additive":
        current = additive_version if isinstance(additive_version, _Version) \
            else Version(additive_version)
    else:
        from webfluid import version
        current = version()

    return current in specifier
