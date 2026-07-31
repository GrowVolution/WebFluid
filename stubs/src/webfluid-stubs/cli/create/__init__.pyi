import typer

from webfluid.cli.create.project import project as project
from webfluid.cli.create.additive import additive as additive
from webfluid.cli.create.create_app import create_app as create_app

create: typer.Typer

def cli_entry(app: typer.Typer) -> None: ...

__all__ = ["create", "project", "additive", "create_app", "cli_entry"]
