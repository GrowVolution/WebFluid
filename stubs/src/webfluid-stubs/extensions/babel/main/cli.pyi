from pathlib import Path

import typer

_CONFIG: Path


class CLIExtension:
    cli: typer.Typer
    @staticmethod
    def extract_fallback(project_root: Path) -> None: ...
    @staticmethod
    def compile_fallback(project_root: Path) -> None: ...
    @staticmethod
    def extract() -> None: ...
    @staticmethod
    def compile() -> None: ...
