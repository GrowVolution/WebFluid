from pathlib import Path
from configparser import ConfigParser
from secrets import token_hex
import typer

from .helpers import setup_additives
from webfluid.cli import questions
from webfluid.core.constants import FEATURE_FLAGS, EXTENSION_FLAGS


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
    enable_extensions = questions.extensions.ask()
    for ext in EXTENSION_FLAGS:
        enabled = ext in enable_extensions
        config["extensions"][ext] = "1" if enabled else "0"

    config["features"] = {}
    enable_features = questions.features.ask()
    for feat in FEATURE_FLAGS:
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
