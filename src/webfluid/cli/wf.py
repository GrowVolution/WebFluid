from importlib.metadata import entry_points
import typer

from webfluid.cli.create import cli_entry as create_cli
from webfluid.cli.ocean import cli_entry as ocean_cli
from webfluid.cli.run import cli_entry as run_cli
from webfluid.surface import node_cli, tailwind_cli
from webfluid.extensions.base import FluidExtension

app = typer.Typer(name="WebFluid CLI")


def cli():
    create_cli(app)
    ocean_cli(app)
    run_cli(app)

    node_cli(app)
    tailwind_cli(app)

    for ep in entry_points(group="webfluid.extensions"):
        ext = ep.load()

        if not issubclass(ext, FluidExtension) or not isinstance(ext, type(FluidExtension)):
            print(typer.style(
                f"Cannot register extension '{ep.name}': not a subclass or instance of FluidExtension.",
                fg=typer.colors.YELLOW
            ))
            continue

        ext.cli_entry(app, ep.name)

    app()
