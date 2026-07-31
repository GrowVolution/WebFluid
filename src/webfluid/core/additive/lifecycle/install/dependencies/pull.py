from pathlib import Path
import typer, sys

from .match import match_version
from webfluid.core.identity import CLI_NAME, HUB_NAME
from webfluid.exceptions import OceanError


def pull_dependency(additive, rid, constraint, additive_root, seen):
    from webfluid.utils.ocean import Ocean, extract_archive, humanize_error

    target = additive_root / rid
    if target.exists() and any(target.iterdir()): return

    ocean = Ocean()
    try: meta = ocean.resolve("additives", rid)
    except OceanError as e:
        typer.echo(typer.style(
            f"[{additive.name}] Could not resolve required additive '{rid}': "
            f"{humanize_error(e.detail)}",
            fg=typer.colors.RED, bold=True
        ))
        return

    version = match_version(meta, constraint)
    if version is None:
        typer.echo(typer.style(
            f"[{additive.name}] No stable release of '{rid}' matches '{constraint}'.",
            fg=typer.colors.RED, bold=True
        ))
        return

    if not meta.get("oss") and not meta.get("owned"):
        typer.echo(typer.style(
            f"[{additive.name}] Required additive '{rid}' is paid and not owned. "
            f"Install it manually with '{CLI_NAME} {HUB_NAME.lower()} install'.",
            fg=typer.colors.RED, bold=True
        ))
        return

    try: data = ocean.download("additives", rid, version)
    except OceanError as e:
        typer.echo(typer.style(
            f"[{additive.name}] Failed to download '{rid}': "
            f"{humanize_error(e.detail)}",
            fg=typer.colors.RED, bold=True
        ))
        return

    extract_archive(data, target)
    typer.echo(typer.style(
        f"[{additive.name}] Pulled required additive '{rid}' {version}.",
        fg=typer.colors.GREEN
    ))

    from importlib import import_module
    project_root = Path.cwd()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    try:
        mod = import_module(f"additives.{target.name}")
        dependency = getattr(mod, "additive", None)
        if dependency is not None and not dependency.is_base:
            dependency.install(seen)
    except Exception as e:
        typer.echo(typer.style(
            f"[{additive.name}] Failed to install pulled additive '{rid}': {e}",
            fg=typer.colors.RED, bold=True
        ))
