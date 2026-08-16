from pathlib import Path
from importlib import import_module
import sys, subprocess, typer

from webfluid.core.identity import CLI_NAME, HUB_NAME
from webfluid.utils.ocean import Ocean, extract_archive, humanize_error
from webfluid.exceptions import OceanError
from webfluid.cli import questions
from webfluid.cli.ocean.output import bundle_id

_channels = {
    "": "stable", "a": "alpha", "b": "beta",
    "rc": "rc", "any": "prerelease"
}
_labels = {
    "": "stable release", "a": "alpha release", "b": "beta release",
    "rc": "release candidate", "any": "prerelease"
}
_bundle_types = { "additive": "additives", "extension": "extensions" }


def _parse_spec(spec):
    if "==" in spec:
        pid, _, version = spec.partition("==")
        return pid.strip(), version.strip() or None
    return spec.strip(), None


def _channel(alpha, beta, rc, pre, prefer_stable):
    selected = [c for c, on in (("a", alpha), ("b", beta), ("rc", rc)) if on]

    if len(selected) > 1:
        order = { "rc": 0, "b": 1, "a": 2 }
        chosen = sorted(selected, key=lambda c: order[c])[0]
        typer.secho(
            "Multiple prerelease channels selected; using the most "
            f"mature one: {_channels[chosen]}.",
            fg=typer.colors.YELLOW
        )
        selected = [chosen]

    if selected:
        if pre: typer.secho(
            f"--pre is ignored next to --{_channels[selected[0]]}.",
            fg=typer.colors.YELLOW
        )
        return selected[0]

    if pre and prefer_stable: typer.secho(
        "--prefer-stable already falls back to the latest prerelease, "
        "so --pre adds nothing next to it.",
        fg=typer.colors.YELLOW
    )
    return "any" if pre else ""


def _wanted(channel, prefer_stable):
    if prefer_stable:
        return f"stable release or {_labels[channel or 'any']}"
    return _labels[channel]


def _matches(version, channel):
    if channel == "any": return bool(version.stage)
    return version.stage == channel


def _latest_in_channel(versions, channel):
    from webfluid.utils.core import Version
    best = None
    for version in versions:
        try: av = Version(version)
        except (ValueError, TypeError): continue
        if not _matches(av, channel): continue
        if best is None or av > best[0]:
            best = (av, version)
    return best[1] if best else None


def _select_version(pid, meta, pinned, channel, prefer_stable=False):
    versions = [release["version"] for release in meta.get("releases", [])]
    if not versions:
        typer.secho(f"[{pid}] No releases available.", fg=typer.colors.RED)
        return None

    if pinned:
        if pinned not in versions:
            typer.secho(
                f"[{pid}] Version '{pinned}' not found. "
                f"Available: {', '.join(versions)}",
                fg=typer.colors.RED
            )
            return None
        return pinned

    chosen = _latest_in_channel(versions, "" if prefer_stable else channel)
    if chosen is None and prefer_stable:
        chosen = _latest_in_channel(versions, channel or "any")

    if chosen is None:
        typer.secho(
            f"[{pid}] No {_wanted(channel, prefer_stable)} available.",
            fg=typer.colors.RED
        )
    return chosen


def _bundle_ref(value):
    ref = str(value).strip().lstrip("0")
    return ref if ref.isdigit() else None


def _pull_bundle(ocean, ref):
    try: return ocean.bundle(ref)
    except OceanError as e:
        if e.status == 404:
            typer.secho(f"[bundle {bundle_id(ref)}] Not found on the {HUB_NAME}.",
                        fg=typer.colors.RED)
        else:
            typer.secho(
                f"[bundle {bundle_id(ref)}] Could not resolve: "
                f"{humanize_error(e.detail)}",
                fg=typer.colors.RED
            )
        return None


def _add_spec(specs, seen, ptype, spec, origin=None):
    pid, _ = _parse_spec(spec)
    if (ptype, pid) in seen:
        typer.secho(
            f"[{pid}] Requested more than once"
            f"{f' (also in {origin})' if origin else ''}; "
            "installing it once.",
            fg=typer.colors.YELLOW
        )
        return
    seen.add((ptype, pid))
    specs[ptype].append(spec)


def _collect(ocean, additives, extensions, bundles):
    specs = { "additives": [], "extensions": [] }
    seen = set()
    expanded = set()

    for ptype, entries in (("additives", additives), ("extensions", extensions)):
        for spec in entries:
            _add_spec(specs, seen, ptype, spec)

    for value in bundles:
        ref = _bundle_ref(value)
        if ref is None:
            typer.secho(f"[{value}] Not a valid bundle id.", fg=typer.colors.RED)
            continue

        label = bundle_id(ref)
        if ref in expanded:
            typer.secho(
                f"[bundle {label}] Requested more than once; expanding it once.",
                fg=typer.colors.YELLOW
            )
            continue
        expanded.add(ref)

        bundle = _pull_bundle(ocean, ref)
        if bundle is None: continue

        items = bundle.get("items") or []
        typer.secho(
            f"[bundle {label}] {bundle.get('name') or ''} "
            f"— {len(items)} package(s).",
            bold=True
        )
        for item in items:
            ptype = _bundle_types.get(item.get("type"))
            if ptype is None: continue
            _add_spec(specs, seen, ptype, item["id"], f"bundle {label}")

    return specs


def _installed_additive_ids(additive_root):
    from webfluid.utils.additives import installed_additives, installed_bases
    ids = set()
    if not additive_root.exists(): return ids
    for entry in installed_additives(additive_root, cache=False):
        ids.add(entry[0])
    for entry in installed_bases(additive_root, cache=False):
        ids.add(entry[0])
    return ids


def _env_has_package(name):
    from importlib.metadata import distribution, PackageNotFoundError
    try:
        distribution(name)
        return True
    except PackageNotFoundError:
        return False


def _pip_install_editable(target):
    typer.secho(f"[{target.name}] Installing extension (pip install -e)...",
                bold=True)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        cwd=target, capture_output=True, text=True
    )
    if result.returncode != 0:
        typer.secho(
            f"[{target.name}] pip install failed:\n{result.stderr.strip()}",
            fg=typer.colors.RED
        )
        return False
    return True


def _install_package(ocean, ptype, pid, pinned, channel, prefer_stable, target):
    if target.exists() and any(target.iterdir()):
        typer.secho(f"[{pid}] Directory '{target}' already exists. Skipping.",
                    fg=typer.colors.YELLOW)
        return False

    try: meta = ocean.resolve(ptype, pid)
    except OceanError as e:
        if e.status == 404:
            typer.secho(f"[{pid}] Not found on the {HUB_NAME}.", fg=typer.colors.RED)
        else:
            typer.secho(f"[{pid}] Could not resolve: {humanize_error(e.detail)}",
                        fg=typer.colors.RED)
        return False

    version = _select_version(pid, meta, pinned, channel, prefer_stable)
    if version is None: return False

    if not meta.get("oss") and not meta.get("owned"):
        if not ocean.authenticated:
            typer.secho(
                f"[{pid}] Paid package. Run '{CLI_NAME} {HUB_NAME.lower()} login' "
                f"and purchase it on the {HUB_NAME} first.",
                fg=typer.colors.RED
            )
        else:
            typer.secho(
                f"[{pid}] You do not own this paid package. "
                f"Purchase it on the {HUB_NAME} first.",
                fg=typer.colors.RED
            )
        return False

    if meta.get("waiver_required"):
        typer.secho(
            f"[{pid}] This is paid digital content. Downloading it now starts "
            "delivery and requires waiving your right of withdrawal.",
            fg=typer.colors.YELLOW
        )
        if not questions.ocean_confirm_waiver(pid).ask():
            typer.secho(f"[{pid}] Withdrawal waiver declined. Skipping.",
                        fg=typer.colors.YELLOW)
            return False
        try:
            ocean.waive(ptype, pid)
        except OceanError as e:
            typer.secho(
                f"[{pid}] Could not record withdrawal waiver: "
                f"{humanize_error(e.detail)}",
                fg=typer.colors.RED
            )
            return False

    try: data = ocean.download(ptype, pid, version)
    except OceanError as e:
        if e.status in (401, 403):
            typer.secho(f"[{pid}] Access denied. Login and ownership required.",
                        fg=typer.colors.RED)
        else:
            typer.secho(f"[{pid}] Download failed: {humanize_error(e.detail)}",
                        fg=typer.colors.RED)
        return False

    extract_archive(data, target)
    typer.secho(f"[{pid}] Installed {ptype[:-1]} {version} -> {target}",
                fg=typer.colors.GREEN)
    return True


def _install_additives(project_root, dirnames):
    if not dirnames: return
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    typer.secho("\nInstalling additives...", bold=True)
    seen = set()
    for dirname in dirnames:
        try:
            mod = import_module(f"additives.{dirname}")
            adtv = getattr(mod, "additive", None)
            if adtv is None:
                typer.secho(f"[{dirname}] Missing 'additive' export. Skipping.",
                            fg=typer.colors.YELLOW)
                continue
            if adtv.is_base: continue
            adtv.install(seen)
            typer.secho(f"[{dirname}] Installed.", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"[{dirname}] Install failed: {e}", fg=typer.colors.RED)


def install(
        additive: list[str] = typer.Option(
            [], "--additive", "-a",
            help="Additive to install (id or id==version). Repeatable."
        ),
        extension: list[str] = typer.Option(
            [], "--extension", "-e",
            help="Extension to install (id or id==version). Repeatable."
        ),
        bundle: list[str] = typer.Option(
            [], "--bundle", "-b",
            help="Bundle id to install as a whole. Repeatable."
        ),
        alpha: bool = typer.Option(
            False, "--alpha", help="Resolve the latest alpha release."
        ),
        beta: bool = typer.Option(
            False, "--beta", help="Resolve the latest beta release."
        ),
        rc: bool = typer.Option(
            False, "--rc", help="Resolve the latest release candidate."
        ),
        pre: bool = typer.Option(
            False, "--pre", "-p",
            help="Resolve the latest prerelease, whatever its channel."
        ),
        prefer_stable: bool = typer.Option(
            False, "--prefer-stable", "-ps",
            help="Resolve the latest stable release, "
                 "falling back to the latest prerelease."
        )
):
    if not additive and not extension and not bundle:
        typer.secho(
            "Nothing to install. Use --additive/-a, --extension/-e "
            "or --bundle/-b.",
            fg=typer.colors.YELLOW
        )
        raise typer.Exit(1)

    channel = _channel(alpha, beta, rc, pre, prefer_stable)
    project_root = Path.cwd()
    ocean = Ocean()

    specs = _collect(ocean, additive, extension, bundle)
    if not specs["additives"] and not specs["extensions"]:
        typer.secho("Nothing left to install.", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    additive_targets = []

    if specs["additives"]:
        additive_root = project_root / "additives"
        additive_root.mkdir(exist_ok=True)
        installed = _installed_additive_ids(additive_root)
        for spec in specs["additives"]:
            pid, pinned = _parse_spec(spec)
            if pid in installed:
                typer.secho(
                    f"[{pid}] An additive or base with this id is already "
                    "installed. Skipping.",
                    fg=typer.colors.YELLOW
                )
                continue
            if _install_package(
                    ocean, "additives", pid, pinned, channel, prefer_stable,
                    additive_root / pid
            ): additive_targets.append(pid)

    if specs["extensions"]:
        extension_root = project_root / "extensions"
        extension_root.mkdir(exist_ok=True)
        for spec in specs["extensions"]:
            pid, pinned = _parse_spec(spec)
            if _env_has_package(pid):
                typer.secho(
                    f"[{pid}] A package named '{pid}' is already installed "
                    "in this environment. Skipping.",
                    fg=typer.colors.YELLOW
                )
                continue
            target = extension_root / pid
            if _install_package(
                    ocean, "extensions", pid, pinned, channel, prefer_stable,
                    target
            ): _pip_install_editable(target)

    if additive_targets:
        _install_additives(project_root, additive_targets)
