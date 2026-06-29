from pathlib import Path
import sys, subprocess, typer

from webfluid.utils.ocean import Ocean, extract_archive, humanize_error
from webfluid.exceptions import OceanError
from webfluid.cli import questions

_channels = { "": "stable", "a": "alpha", "b": "beta", "rc": "rc" }


def _parse_spec(spec: str) -> tuple[str, str | None]:
    if "==" in spec:
        pid, _, version = spec.partition("==")
        return pid.strip(), version.strip() or None
    return spec.strip(), None


def _channel(alpha: bool, beta: bool, rc: bool) -> str:
    selected = [c for c, on in (("a", alpha), ("b", beta), ("rc", rc)) if on]
    if len(selected) > 1:
        order = { "rc": 0, "b": 1, "a": 2 }
        chosen = sorted(selected, key=lambda c: order[c])[0]
        typer.secho(
            "Multiple prerelease channels selected; using the most "
            f"mature one: {_channels[chosen]}.",
            fg=typer.colors.YELLOW
        )
        return chosen
    return selected[0] if selected else ""


def _latest_in_channel(versions: list[str], channel: str) -> str | None:
    from webfluid.core.additive import AdditiveVersion
    best = None
    for version in versions:
        try: av = AdditiveVersion(*version.split("."))
        except (ValueError, TypeError): continue
        if av.stage != channel: continue
        key = (tuple(av), av.build)
        if best is None or key > best[0]:
            best = (key, version)
    return best[1] if best else None


def _select_version(pid: str, meta: dict, pinned: str | None,
                    channel: str) -> str | None:
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

    chosen = _latest_in_channel(versions, channel)
    if chosen is None:
        typer.secho(
            f"[{pid}] No {_channels[channel]} release available.",
            fg=typer.colors.RED
        )
    return chosen


def _installed_additive_ids(additive_root: Path) -> set[str]:
    from webfluid.utils.additives import installed_additives, installed_bases
    ids = set()
    if not additive_root.exists(): return ids
    for entry in installed_additives(additive_root, cache=False):
        ids.add(entry[0])
    for entry in installed_bases(additive_root, cache=False):
        ids.add(entry[0])
    return ids


def _env_has_package(name: str) -> bool:
    from importlib.metadata import distribution, PackageNotFoundError
    try:
        distribution(name)
        return True
    except PackageNotFoundError:
        return False


def _pip_install_editable(target: Path) -> bool:
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


def _install_package(ocean: Ocean, ptype: str, pid: str,
                     pinned: str | None, channel: str, target: Path) -> bool:
    if target.exists() and any(target.iterdir()):
        typer.secho(f"[{pid}] Directory '{target}' already exists. Skipping.",
                    fg=typer.colors.YELLOW)
        return False

    try:
        meta = ocean.resolve(ptype, pid)
    except OceanError as e:
        if e.status == 404:
            typer.secho(f"[{pid}] Not found on the Ocean.", fg=typer.colors.RED)
        else:
            typer.secho(f"[{pid}] Could not resolve: {humanize_error(e.detail)}",
                        fg=typer.colors.RED)
        return False

    version = _select_version(pid, meta, pinned, channel)
    if version is None: return False

    if not meta.get("oss") and not meta.get("owned"):
        if not ocean.authenticated:
            typer.secho(
                f"[{pid}] Paid package. Run 'wf ocean login' and purchase "
                "it on the Ocean first.",
                fg=typer.colors.RED
            )
        else:
            typer.secho(
                f"[{pid}] You do not own this paid package. "
                "Purchase it on the Ocean first.",
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

    try:
        data = ocean.download(ptype, pid, version)
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


def _install_additives(project_root: Path, dirnames: list[str]):
    from importlib import import_module

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
        alpha: bool = typer.Option(
            False, "--alpha", help="Resolve the latest alpha release."
        ),
        beta: bool = typer.Option(
            False, "--beta", help="Resolve the latest beta release."
        ),
        rc: bool = typer.Option(
            False, "--rc", help="Resolve the latest release candidate."
        )
):
    if not additive and not extension:
        typer.secho("Nothing to install. Use --additive/-a or --extension/-e.",
                    fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    channel = _channel(alpha, beta, rc)
    project_root = Path.cwd()
    ocean = Ocean()

    additive_targets: list[str] = []

    if additive:
        additive_root = project_root / "additives"
        additive_root.mkdir(exist_ok=True)
        installed = _installed_additive_ids(additive_root)
        for spec in additive:
            pid, pinned = _parse_spec(spec)
            if pid in installed:
                typer.secho(
                    f"[{pid}] An additive or base with this id is already "
                    "installed. Skipping.",
                    fg=typer.colors.YELLOW
                )
                continue
            if _install_package(
                    ocean, "additives", pid, pinned, channel,
                    additive_root / pid
            ): additive_targets.append(pid)

    if extension:
        extension_root = project_root / "extensions"
        extension_root.mkdir(exist_ok=True)
        for spec in extension:
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
                    ocean, "extensions", pid, pinned, channel, target
            ): _pip_install_editable(target)

    if additive_targets:
        _install_additives(project_root, additive_targets)
