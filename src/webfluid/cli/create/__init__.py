import typer

create = typer.Typer(help="Create new WebFluid instances.")

from .project import project
from .additive import additive
from .create_app import create_app

create.command()(project)
create.command()(additive)
create.command("app")(create_app)


def cli_entry(app):
    app.add_typer(create, name="create")
