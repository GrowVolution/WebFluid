import typer

from webfluid.cli.run.main import run as run

def cli_entry(app: typer.Typer) -> None: ...

__all__ = ["run", "cli_entry"]
