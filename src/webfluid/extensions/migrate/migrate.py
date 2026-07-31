from pathlib import Path
from configparser import ConfigParser
from datetime import datetime, UTC
import subprocess, shutil, typer, os, sys

from webfluid.extensions.base import FluidExtension
from webfluid.core.config.main import Config
from webfluid.core.config.init import init_configs
from webfluid.core.config.build import build_config
from webfluid.utils.core import parse_config

_templates = Path(__file__).parent / "templates"


def _manipulated_env(app):
    cfg = ConfigParser()
    cfg.optionxform = str
    cfg.read(Path.cwd() / "app_configs" / f"{app}.ini")
    env = os.environ.copy()
    pairs = [parse_config(k, v) for k, v in cfg.defaults().items()]
    for k, v in pairs: env[k] = v
    for section in cfg.sections():
        pairs = [parse_config(k, v) for k, v in cfg[section].items()]
        for k, v in pairs: env[k] = v
    env["EXT_SQLALCHEMY"] = "1"
    env["EXT_EVENTS"] = "0"
    env["EXT_CACHE"] = "0"
    env["EXT_MAIL"] = "0"
    env["EXT_JWT"] = "0"
    env["WF_THEMES"] = "0"
    env["WF_TAILWIND"] = "0"
    env["WF_PROCESSING"] = "0"
    return env


class Migrate(FluidExtension):
    _cli = typer.Typer(help="WebFluid Migrate CLI")

    @staticmethod
    @_cli.command()
    def init(app: str):
        project_root = Path.cwd()

        (project_root / "migrate").mkdir(exist_ok=True)
        migrations_dir = project_root / "migrate" / f"migrations_{app}"
        alembic_ini = project_root / "migrate" / f"alembic_{app}.ini"

        if migrations_dir.exists() or alembic_ini.exists():
            typer.secho(
                f"[{app}] Migration environment already initialized.",
                fg=typer.colors.YELLOW
            )
            raise typer.Exit()

        class Dummy: project_root = project_root
        sys.path.insert(0, str(project_root))
        try: init_configs(Dummy)
        finally: sys.path.pop(0)
        config = Config()
        config.update(build_config())

        binds = config.get("SQLALCHEMY_BINDS", {})
        template = "multi_db" if binds else "single_db"
        template_dir = _templates / template

        typer.echo(f"Using '{template}' migration template.")

        shutil.copytree(
            template_dir / "migrations",
            migrations_dir
        )
        alembic_ini.write_text(
            (template_dir / "alembic.ini.mako").read_text()
            .format(app=app)
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
        base_cmd = ["alembic", "-c", f"migrate/alembic_{app}.ini", "revision"]
        if autogenerate: base_cmd.append("--autogenerate")
        base_cmd += ["-m", f"[{app}] "
                           f"[{datetime.now(UTC).strftime('%Y-%m-%d_%H-%M-%S')}] "
                           f"{message}"]
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
            ["alembic", "-c", f"migrate/alembic_{app}.ini",
             "upgrade", "head"],
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
            ["alembic", "-c", f"migrate/alembic_{app}.ini",
             "downgrade", revision],
            check=True,
            env=_manipulated_env(app),
            cwd=Path.cwd()
        )
