from pathlib import Path
from typing import Callable
import json

from webfluid.utils import check_required_version, enabled
from webfluid.utils.additive import id_check, version_check, type_check, frontend_check
from webfluid.utils.logging import factory as log_factory
from webfluid.exceptions import AdditiveException, ManifestError


class Manifest:

    structure = {
        # field: (type, required, Optional[check_fn])
        "id": (str, True, id_check),
        "version": (str, True, version_check),
        "type": (str, True, type_check),
        "frontend": (dict[str, str | bool], True, frontend_check),
        "name": (str, False),
        "description": (str, False),
        "authors": (list[dict[str, str]], False),
        "requires": (dict[str, str | list[str] | dict[str, str]], False)
    }

    def __init__(self, manifest_file: Path):
        if not manifest_file.exists():
            raise FileNotFoundError("Missing manifest.")

        try:
            self._data = json.loads(manifest_file.read_text())
        except json.decoder.JSONDecodeError:
            raise ManifestError("Invalid manifest format.")

        for field, info in self.structure.items():
            if not info[1]: continue

            data = self.get(field)
            if not data:
                raise ManifestError(f"Missing required field '{field}'.")

            data_type = info[0]
            if not isinstance(data, data_type):
                try: data = data_type(data)
                except (ValueError, TypeError) as e:
                    raise ManifestError(f"Invalid data type '{data_type}' for field '{field}': {e}")

            result = info[2](data)
            if not result[0]:
                raise ManifestError(result[1])
            self[field] = result[1]

        if self["type"] == "base" and self["frontend"]["type"] != "none":
            raise ManifestError("Base additives cannot have a frontend.")

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, item):
        return item in self._data

    def __len__(self):
        return len(self._data)

    def check_requirements(self, additive_root: Path):
        if not "requires" in self:
            return

        requirements = self["requires"]
        if not "wf" in requirements:
            log_factory.warning(f"[{self['name']}] Required WebFluid version of not defined.")
        else:
            fulfilled = check_required_version(requirements["wf"])
            if not fulfilled:
                raise AdditiveException(
                    f"[{self['name']}] Additive requires WebFluid version {requirements['wf']}."
                )

        if "additives" in requirements:
            from webfluid.additives import installed_additives, import_base
            additives = installed_additives(additive_root)
            requirement = requirements["additives"]

            if isinstance(requirement, list):
                new = {}
                for r in requirement:
                    if not isinstance(r, str):
                        raise ManifestError(f"[{self['name']}] Invalid additive requirement '{r}'.")
                    r = r.split("@")
                    if len(r) == 2:
                        a, v = r
                    else:
                        a = r[0]
                        v = "*"
                    new[a] = v
                requirement = new

            if not isinstance(requirement, dict):
                raise ManifestError(f"[{self['name']}] Invalid additives requirement type: {type(requirement)}")

            requirement_copy = requirement.copy()

            for additive in additives:
                a, v, _ = additive
                if a not in requirement:
                    continue

                if not enabled(a):
                    continue

                if check_required_version(requirement.get(a, "*"), "additive", v):
                    requirement_copy.pop(a)

            requirement = requirement_copy.copy()

            for a, v in requirement.items():
                base = import_base(a)
                if base and check_required_version(v, "additive", base.version):
                    requirement_copy.pop(a)

            if len(requirement_copy) > 0:
                raise AdditiveException(
                    f"[{self['name']}] Missing or mismatching additive requirements: {[a for a in requirement_copy]}"
                )

    @property
    def get(self) -> Callable:
        return self._data.get

    @property
    def pop(self) -> Callable:
        return self._data.pop
