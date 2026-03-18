from pathlib import Path
from configparser import ConfigParser
import subprocess, shutil, typer, os, sys

from webfluid.extensions.base import FluidExtension
from webfluid.core.config import Config, init_configs, build_config

_templates = Path(__file__).parent / "templates"


def _manipulated_env(app: str) -> dict:
    cfg = ConfigParser()
    cfg.optionxform = str
    cfg.read(Path.cwd() / "app_configs" / f"{app}.ini")
    env = os.environ.copy()
    for k, v in cfg.defaults().items():
        env[k] = v
    for section in cfg.sections():
        for k, v in cfg[section].items():
            env[k] = v
    env["EXT_SQLALCHEMY"] = "1"
    env["EXT_BABEL"] = "1"
    return env


class Migrate(FluidExtension):
    _cli = typer.Typer(help="WebFluid Migrate CLI")

    @staticmethod
    @_cli.command()
    def init():
        project_root = Path.cwd()

        migrations_dir = project_root / "migrations"
        alembic_ini = project_root / "alembic.ini"

        if migrations_dir.exists() or alembic_ini.exists():
            typer.secho(
                "Migration environment already initialized.",
                fg=typer.colors.YELLOW
            )
            raise typer.Exit()

        class Dummy: app_root = project_root
        sys.path.append(str(project_root))
        init_configs(Dummy)
        config = Config()
        config.from_object(build_config())

        binds = config.get("SQLALCHEMY_BINDS", {})
        template = "multi_db" if binds else "single_db"
        template_dir = _templates / template

        typer.echo(f"Using '{template}' migration template.")

        shutil.copytree(
            template_dir / "migrations",
            migrations_dir
        )
        shutil.copyfile(
            template_dir / "alembic.ini.mako",
            alembic_ini
        )
        (migrations_dir / "versions").mkdir(exist_ok=True)

        typer.secho(
            "Migration environment created.",
            fg=typer.colors.GREEN
        )

    @staticmethod
    @_cli.command()
    def revision(
            app: str,
            message: str = typer.Option(
                "",
                "--message", "-m",
            ),
            autogenerate: bool = typer.Option(
                False,
                "--autogenerate", "-a"
            )
    ):
        base_cmd = ["alembic", "revision"]
        if autogenerate: base_cmd.append("--autogenerate")
        base_cmd += ["-m", message]
        subprocess.run(
            base_cmd,
            check=True,
            env=_manipulated_env(app),
            cwd=Path.cwd()
        )

    @staticmethod
    @_cli.command()
    def upgrade(app: str):
        subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            env=_manipulated_env(app),
            cwd=Path.cwd()
        )

    @staticmethod
    @_cli.command()
    def downgrade(
            app: str,
            revision: str = typer.Option(
                "-1",
                "--revision", "-r"
            )
    ):
        subprocess.run(
            ["alembic", "downgrade", revision],
            check=True,
            env=_manipulated_env(app),
            cwd=Path.cwd()
        )
