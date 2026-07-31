import typer

from webfluid.core.identity import FRAMEWORK_NAME

create = typer.Typer(help=f"Create new {FRAMEWORK_NAME} instances.")

from .project import project
from .additive import additive
from .create_app import create_app

create.command()(project)
create.command()(additive)
create.command("app")(create_app)


def cli_entry(app):
    app.add_typer(create, name="create")
