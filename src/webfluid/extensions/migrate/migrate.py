from pathlib import Path
import subprocess, shutil, typer

from webfluid.utils.config import init_configs, build_config


class Migrate:
    _cli = typer.Typer(help="WebFluid Migrate CLI")
    _templates = Path(__file__).parent / "templates"

    @classmethod
    @_cli.command()
    def init(cls):

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
        init_configs(Dummy)
        config = build_config()

        binds = config.get("SQLALCHEMY_BINDS", {})
        template = "multi_db" if binds else "single_db"
        template_dir = cls._templates / template

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
            message: str,
            autogenerate: bool = typer.Option(
                False,
                "--autogenerate", "-a"
            )
    ):
        base_cmd = ["alembic", "revision"]
        if autogenerate: base_cmd.append("--autogenerate")
        base_cmd += ["-m", message]
        subprocess.run(base_cmd, check=True)

    @staticmethod
    @_cli.command()
    def upgrade():
        subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True
        )

    @staticmethod
    @_cli.command()
    def downgrade(revision: str = "-1"):
        subprocess.run(
            ["alembic", "downgrade", revision],
            check=True
        )

    @classmethod
    def cli_entry(cls, app: typer.Typer):
        app.add_typer(cls._cli, name="migrate")
