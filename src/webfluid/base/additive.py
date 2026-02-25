from flask.helpers import get_root_path
from pathlib import Path
from typing import Callable, TYPE_CHECKING
import json, typer, subprocess, sys

from webfluid.utils import check_required_version, enabled
from webfluid.utils.additive import id_check, version_check, type_check, require_extensions
from webfluid.utils.logging import factory as log_factory
from webfluid.exceptions import AdditiveException, ManifestError

if TYPE_CHECKING:
    from webfluid import Fluid


class AdditiveVersion(tuple):
    def __new__(cls, major: int, minor: int | None = None, patch: int | None = None):
        minor = 0 if minor is None else minor
        patch = 0 if patch is None else patch
        return super().__new__(cls, (major, minor, patch))

    @property
    def length(self) -> int:
        if self[2] != 0:
            return 3
        if self[1] != 0:
            return 2
        return 1

    def __str__(self) -> str:
        return f"v{'.'.join(map(str, self[:self.length]))}"


class BaseAdditive:
    def __init__(self, import_name: str, base: "BaseAdditive" = None,
                 required_extensions: list = None, allow_frontend: bool = True):

        if not "additives." in import_name:
            raise AdditiveException("Additives have to be created inside the 'additives' package.")

        self.additive_name = import_name.split(".")[-1]
        self.import_name = import_name
        self.root_path = Path(get_root_path(import_name)).resolve()

        try: self.manifest = Manifest(self.root_path / "manifest.json")
        except (FileNotFoundError, ManifestError) as e:
            raise AdditiveException(f"[{self.additive_name}] Failed to load manifest: {e}")

        if not "name" in self.manifest:
            self.manifest["name"] = self.additive_name
        else:
            self.additive_name = self.manifest["name"]

        self.is_base = self.manifest["type"] == "base"
        self.required_extensions = required_extensions or []

        if base and self.is_base:
            raise AdditiveException(f"[{self.additive_name}] Base additives cannot extend other additives.")
        elif base and not base.is_base:
            raise AdditiveException(f"[{self.additive_name}] Default additives can only extend base additives.")

        self.base = base
        self.parent = None
        if base: self.required_extensions.extend(base.required_extensions or [])
        self.enable = log_factory.additive_context(
            require_extensions(*self.required_extensions)(self._enable)
        )
        self._allow_frontend = allow_frontend

        self._handlers = {
            "async": {},
            "sync": {}
        }

    def __repr__(self) -> str:
        return f"<{self.additive_name} {self.version}> {self.manifest.get('description', '')}"

    def _enable(self, app: "Fluid"): raise NotImplementedError()

    def _extract(self):
        extract_path = Path(self.root_path) / "extract"

        def for_dir(path, name):
            for file in (path / name).rglob("*"):
                if not file.is_file():
                    continue

                rel = file.relative_to(path)
                dst = Path.cwd() / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists():
                    typer.echo(typer.style(
                        f"[{self.additive_name}] Could not extract '{'/'.join(rel.parts)}': "
                        "File already exists.", fg=typer.colors.YELLOW
                    ))
                    continue

                typer.echo(f"[{self.additive_name}] Extracting '{'/'.join(rel.parts)}'.")

                dst.write_bytes(
                    file.read_bytes()
                )

        for_dir(extract_path, "static")
        for_dir(extract_path, "templates")

        typer.echo(typer.style(
            f"[{self.additive_name}] Finished extracting additives extract files to main app.",
            fg=typer.colors.GREEN, bold=True
        ))

    def _install_packages(self):
        if not "requires" in self.manifest: return
        requirements = self.manifest["requires"]
        if not "packages" in requirements: return

        packages = requirements["packages"]
        if not isinstance(packages, list):
            typer.echo(typer.style(
                f"[{self.additive_name}] Invalid packages requirement type: {type(packages)}",
                fg=typer.colors.YELLOW, bold=True
            ))
            return

        for package in packages:
            typer.echo(f"[{self.additive_name}] Installing required package '{package}'...")

            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", package],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                typer.echo(typer.style(
                    f"[{self.additive_name}] Failed to install package '{package}': {result.stderr}",
                    fg=typer.colors.RED, bold=True
                ))

    def install(self):
        if self.base:
            self.base._extract()
            self.base._install_packages()
        self._extract()
        self._install_packages()

    @property
    def version(self) -> AdditiveVersion:
        version_str = self.manifest["version"]
        return AdditiveVersion(*map(int, version_str.split(".")))


class Manifest:

    structure = {
        # field: (type, required, Optional[check_fn])
        "id": (str, True, id_check),
        "version": (str, True, version_check),
        "type": (str, True, type_check),
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
            log_factory.warn(f"[{self['name']}] Required WebFluid version of not defined.")
        else:
            fulfilled = check_required_version(requirements["wf"])
            if not fulfilled:
                raise AdditiveException(
                    f"[{self['name']}] Additive requires WebFluid version {requirements['wf']}."
                )

        if "additives" in requirements:
            from webfluid.additives import installed_additives, import_base
            additives = installed_additives(additive_root, False)
            requirement = requirements["additives"]

            if isinstance(requirement, list):
                new = {}
                for r in requirement:
                    if not isinstance(r, str):
                        raise ManifestError(f"[{self['name']}] Invalid additive requirement '{r}'.")
                    r = r.split("@")
                    if len(r) == 2:
                        m, v = r
                    else:
                        m = r[0]
                        v = "*"
                    new[m] = v
                requirement = new

            if not isinstance(requirement, dict):
                raise ManifestError(f"[{self['name']}] Invalid additives requirement type: {type(requirement)}")

            requirement_copy = requirement.copy()

            for additive in additives:
                m, v, _ = additive
                if m not in requirement:
                    continue

                if not enabled(m):
                    continue

                if check_required_version(requirement.get(m, "*"), "additive", v):
                    requirement_copy.pop(m)

            requirement = requirement_copy.copy()

            for m, v in requirement.items():
                base = import_base(m)
                if base and check_required_version(v, "additive", base.version):
                    requirement_copy.pop(m)

            if len(requirement_copy) > 0:
                raise AdditiveException(
                    f"[{self['name']}] Missing or mismatching additive requirements: {[m for m in requirement_copy]}"
                )

    @property
    def get(self) -> Callable:
        return self._data.get

    @property
    def pop(self) -> Callable:
        return self._data.pop
