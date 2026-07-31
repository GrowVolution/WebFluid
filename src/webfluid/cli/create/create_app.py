from pathlib import Path
from configparser import ConfigParser
from secrets import token_hex
import typer

from .helpers import setup_additives
from webfluid.cli import questions


def create_app(
        name: str,
        secret_length: int = typer.Option(
            32,
            "--secret-length", "-sl",
            help="Length of the secret key."
        )
):
    config_root = Path("app_configs").resolve()
    config_root.mkdir(exist_ok=True)

    config_file = config_root / f"{name}.ini"
    if config_file.exists():
        typer.secho(
            f"Config file '{name}.ini' already exists.",
            fg=typer.colors.RED
        )
        raise typer.Exit(1)

    config = ConfigParser()
    config.optionxform = str

    config["general"] = {
        "SECRET_KEY": token_hex(secret_length)
    }

    config["extensions"] = {}
    extensions = (
        "EXT_SCHEDULING",
        "EXT_SQLALCHEMY",
        "EXT_BABEL",
        "EXT_SECURITY",
        "EXT_EVENTS",
        "EXT_CACHE",
        "EXT_MAIL",
        "EXT_JWT"
    )
    enable_extensions = questions.extensions.ask()
    for ext in extensions:
        enabled = ext in enable_extensions
        config["extensions"][ext] = "1" if enabled else "0"

    config["features"] = {}
    features = (
        "WF_THEMES",
        "WF_TAILWIND",
        "WF_CHECK_FRONTEND",
        "WF_BUILD_FRONTEND",
        "WF_PROCESSING",
        "WF_ADDITIVES"
    )
    enable_features = questions.features.ask()
    for feat in features:
        enabled = feat in enable_features
        config["features"][feat] = "1" if enabled else "0"

    setup_additives(config)

    if "EXT_SECURITY" in enable_extensions:
        config["security"] = {
            "SECURITY_SECRET": token_hex(32)
        }

    print()
    config["data"] = {
        "DATABASE_URI": questions.database_uri(name),
        "REDIS_URI": questions.redis_uri.ask()
    }

    if "EXT_MAIL" in enable_extensions:
        print()
        config["mail"] = {
            "MAIL_USERNAME": questions.mail_username.ask(),
            "MAIL_PASSWORD": questions.mail_password.ask()
        }

    with open(config_file, "w") as f: config.write(f)
