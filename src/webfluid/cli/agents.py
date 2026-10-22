from pathlib import Path
import typer

from webfluid.utils import agents as docs

agents = typer.Typer(help="Keep the agent documentation of a project, an Additive or an extension navigable.")


def _shown(path):
    try: return path.resolve().relative_to(Path.cwd()).as_posix()
    except ValueError: return path.as_posix()


def index(
    paths: list[Path] = typer.Argument(None, help="Files to index. Default: every CONTRACT.md and .agents Markdown file below the current directory."),
    check: bool = typer.Option(False, "--check", help="Change nothing; exit with 1 when an index is out of date.")
):
    targets = paths or docs.discover(Path.cwd())
    if not targets:
        typer.secho("No CONTRACT.md or .agents Markdown file found.", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    stale = []
    for path in targets:
        changed = docs.index(path, write=not check)
        if changed: stale.append(path)
        state = ("stale" if check else "updated") if changed else "current"
        typer.echo(f"{_shown(path)}: {state}")

    if check and stale: raise typer.Exit(1)


agents.command()(index)


def cli_entry(app):
    app.add_typer(agents, name="agents")
