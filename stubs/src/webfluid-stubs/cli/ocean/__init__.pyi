import typer

from webfluid.cli.ocean.search import search as search
from webfluid.cli.ocean.install import install as install
from webfluid.cli.ocean.publish import publish as publish
from webfluid.cli.ocean.auth import login as login, logout as logout

ocean: typer.Typer

def cli_entry(app: typer.Typer) -> None: ...
