import typer

ocean = typer.Typer(help="Browse, publish and install packages from the Ocean.")

from webfluid.cli.ocean.search import search
from webfluid.cli.ocean.install import install
from webfluid.cli.ocean.publish import publish
from webfluid.cli.ocean.auth import login, logout

ocean.command()(search)
ocean.command()(install)
ocean.command()(publish)
ocean.command()(login)
ocean.command()(logout)


def cli_entry(app):
    app.add_typer(ocean, name="ocean")
