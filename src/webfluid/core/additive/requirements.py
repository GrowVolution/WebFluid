from webfluid.utils.core import check_required_version, enabled
from webfluid.utils.logging import factory as log_factory
from webfluid.exceptions import AdditiveException, ManifestError


def normalize(requirement, name):
    if isinstance(requirement, list):
        normalized = {}
        for entry in requirement:
            if not isinstance(entry, str):
                raise ManifestError(f"[{name}] Invalid additive requirement '{entry}'.")
            rid, _, version = entry.partition("@")
            normalized[rid] = version or "*"
        return normalized

    if not isinstance(requirement, dict):
        raise ManifestError(
            f"[{name}] Invalid additives requirement type: {type(requirement)}"
        )

    return dict(requirement)


class RequirementChecker:
    def __init__(self, manifest, additive_root):
        self.manifest = manifest
        self.additive_root = additive_root
        self.name = manifest.get("name") or manifest["id"]

    def check(self):
        requirements = self.manifest.get("requires")
        if not requirements: return

        self._check_framework(requirements)
        if "additives" in requirements:
            self._check_additives(requirements["additives"])

    def _check_framework(self, requirements):
        if "wf" not in requirements:
            log_factory.warning(
                f"[{self.name}] Required WebFluid version of not defined."
            )
            return

        if not check_required_version(requirements["wf"]):
            raise AdditiveException(
                f"[{self.name}] Additive requires WebFluid version {requirements['wf']}."
            )

    def _check_additives(self, requirement):
        from webfluid.utils.additives import installed_additives, installed_bases

        missing = normalize(requirement, self.name)

        for aid, version, _ in installed_additives(self.additive_root):
            if aid not in missing or not enabled(aid): continue
            if check_required_version(missing[aid], "additive", version):
                missing.pop(aid)

        if missing:
            for bid, version, _ in installed_bases(self.additive_root):
                if bid not in missing: continue
                if check_required_version(missing[bid], "additive", version):
                    missing.pop(bid)

        if missing:
            raise AdditiveException(
                f"[{self.name}] Missing or mismatching additive "
                f"requirements: {list(missing)}"
            )
