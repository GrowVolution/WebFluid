from pathlib import Path

import typer

agents: typer.Typer

def index(paths: list[Path] = ..., check: bool = ...) -> None: ...
def cli_entry(app: typer.Typer) -> None: ...
