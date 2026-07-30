from pathlib import Path
import typer, subprocess, sys

from webfluid.core.constants import FRAMEWORK_ROOT

_CONFIG = Path(__file__).parent.parent / "babel.cfg"


class CLIExtension:
    cli = typer.Typer(help="WebFluid Babel CLI")

    @staticmethod
    def extract_fallback(project_root):
        pot = "messages.pot"
        trans = project_root / "translations"
        babel_cli = "babel.messages.frontend"
        has_catalogs = any(trans.glob("*/LC_MESSAGES/*.po"))

        subprocess.run(
            [sys.executable, "-m", babel_cli, "extract",
             "-F", str(_CONFIG),
             "-o", pot,
             str(project_root), str(FRAMEWORK_ROOT)],
            check=True
        )

        if has_catalogs:
            subprocess.run(
                [sys.executable, "-m", babel_cli, "update",
                 "-i", pot,
                 "-d", str(trans)],
                check=True
            )

        else:
            subprocess.run(
                [sys.executable, "-m", babel_cli, "init",
                 "-i", pot,
                 "-d", str(trans),
                 "-l", "en"],
                check=True
            )

    @staticmethod
    def compile_fallback(project_root):
        babel_cli = "babel.messages.frontend"
        subprocess.run(
            [sys.executable, "-m", babel_cli, "compile",
             "-d", str(project_root / "translations")],
            check=True
        )

    @staticmethod
    @cli.command()
    def extract(): CLIExtension.extract_fallback(Path.cwd())

    @staticmethod
    @cli.command()
    def compile(): CLIExtension.compile_fallback(Path.cwd())
