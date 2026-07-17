from pathlib import Path
import typer

from .pull import pull_dependency
from ..requirements import required_additives


def resolve_dependencies(additive, seen):
    required = required_additives(additive)
    if not required: return

    from webfluid.utils.core import check_required_version
    from webfluid.utils.additives import installed_additives, installed_bases

    additive_root = Path.cwd() / "additives"
    additive_root.mkdir(exist_ok=True)

    installed = {}
    for entry in installed_additives(additive_root, cache=False):
        installed[entry[0]] = entry[1]
    for entry in installed_bases(additive_root, cache=False):
        installed[entry[0]] = entry[1]

    for rid, constraint in required.items():
        if rid in seen: continue

        if rid in installed:
            version = installed[rid]
            try: matches = check_required_version(constraint, "additive", version)
            except ValueError: matches = True
            if not matches:
                typer.echo(typer.style(
                    f"[{additive.name}] Installed additive '{rid}' ({version}) does not "
                    f"match the required version '{constraint}'.",
                    fg=typer.colors.YELLOW, bold=True
                ))
            continue

        pull_dependency(additive, rid, constraint, additive_root, seen)
