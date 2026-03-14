import typer

from webfluid.cli.create import cli_entry as create_cli
from webfluid.surface import node_cli, tailwind_cli
from webfluid.extensions.migrate import Migrate

app = typer.Typer(
    name="WebFluid CLI",
    help=typer.style(
        "wf [-h|--help]",
        fg=typer.colors.BLUE,
        bold=True
    )
)


def cli():
    node_cli(app)
    tailwind_cli(app)

    create_cli(app)

    Migrate.cli_entry(app)

    app()
