import typer

from webfluid.utils import ocean as ocean_utils
from webfluid.utils.ocean import Ocean, humanize_error
from webfluid.exceptions import OceanError
from webfluid.cli import questions


def login():
    existing = ocean_utils.load_token()
    if existing:
        try: info = Ocean(token=existing).token_info()
        except OceanError: info = None

        if info is not None:
            confirmed = questions.ocean_confirm_overwrite(
                info.get("username"), info.get("valid_days")
            ).ask()
        else:
            typer.secho("Your existing token could not be validated.",
                        fg=typer.colors.YELLOW)
            confirmed = questions.ocean_confirm_overwrite_invalid().ask()

        if not confirmed:
            typer.secho("Keeping the existing token.", fg=typer.colors.YELLOW)
            raise typer.Exit()

    token = questions.ocean_token.ask()
    if not token or not token.strip():
        typer.secho("No token provided. Aborting.", fg=typer.colors.YELLOW)
        raise typer.Exit(1)
    token = token.strip()

    try:
        result = Ocean(token=token).login_check()
    except OceanError as e:
        typer.secho(f"Login failed: {humanize_error(e.detail)}",
                    fg=typer.colors.RED)
        raise typer.Exit(1)

    ocean_utils.save_token(token)
    typer.secho(
        f"Successfully logged in as {result.get('username')}. "
        f"Your token is valid for {result.get('valid_days')} more days.",
        fg=typer.colors.GREEN, bold=True
    )


def logout():
    if ocean_utils.delete_token():
        typer.secho("Logged out. Token removed.", fg=typer.colors.GREEN)
    else:
        typer.secho("You are not logged in.", fg=typer.colors.YELLOW)
