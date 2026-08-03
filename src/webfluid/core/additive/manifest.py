import json

from webfluid.utils.additives import id_check, version_check, type_check
from webfluid.utils.surface import validate_config as frontend_check
from webfluid.exceptions import ManifestError


class Manifest:

    structure = {
        "id": (str, True, id_check),
        "version": (str, True, version_check),
        "type": (str, True, type_check),
        "frontend": (dict, True, frontend_check),
        "name": (str, False),
        "description": (str, False),
        "authors": (list, False),
        "requires": (dict, False)
    }

    def __init__(self, manifest_file):
        if not manifest_file.exists():
            raise FileNotFoundError("Missing manifest.")

        try:
            self._data = json.loads(
                manifest_file.read_text(encoding="utf-8")
            )
        except json.decoder.JSONDecodeError:
            raise ManifestError("Invalid manifest format.")

        self._data = Manifest.validated_data(self._data)

    def __repr__(self): return f"<Manifest {self['id']}>"
    def __getitem__(self, key): return self._data[key]
    def __setitem__(self, key, value): self._data[key] = value
    def __contains__(self, item): return item in self._data
    def __len__(self): return len(self._data)
    def __str__(self): return str(self._data)

    def keys(self): return self._data.keys()
    def values(self): return self._data.values()
    def items(self): return self._data.items()
    def get(self, key, default=None): return self._data.get(key, default)
    def pop(self, key, default=None): return self._data.pop(key, default)

    def check_requirements(self, additive_root):
        from .requirements import RequirementChecker
        RequirementChecker(self, additive_root).check()

    @classmethod
    def validated_data(cls, target):
        for field, info in cls.structure.items():
            if not info[1]: continue

            data = target.get(field)
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
            target[field] = result[1]

        if target["type"] == "base" and target["frontend"]["type"] != "none":
            raise ManifestError("Base additives cannot have a frontend.")

        return target
