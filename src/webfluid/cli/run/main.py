from pathlib import Path
import typer, os

from webfluid.cli import questions


def run(
        name: str,
        host: str = typer.Option(
            None,
            "--host", "-h",
            help="Host to run the application on."
        ),
        port: int = typer.Option(
            None,
            "--port", "-p",
            help="Port to run the application on."
        ),
        loglevel: str = typer.Option(
            "info",
            "--loglevel", "-l",
            help="Log level to use."
        ),
        interactive: bool = typer.Option(
            False,
            "--interactive", "-i",
            help="Run the application in interactive mode."
        ),
        debug: bool = typer.Option(
            False,
            "--debug", "-d",
            help="Run the application in debug mode."
        )
):
    project_root = Path.cwd()
    config_file = project_root / "app_configs" / f"{name}.ini"
    if not config_file.exists():
        typer.secho(
            f"Config file '{name}.ini' does not exist.",
            fg=typer.colors.RED
        )
        typer.echo(f"Try: {typer.style(f'wf create app {name}', bold=True)} "
                   "and then run this command again.")
        raise typer.Exit(1)

    if not (project_root / "main.py").exists():
        typer.secho(
            f"Missing main.py file in project root.",
            fg=typer.colors.RED
        )
        raise typer.Exit(1)

    from .helpers import env_from_config
    env = env_from_config(config_file, debug)
    if interactive:
        if not host:  host = questions.host.ask()
        if not port: port = questions.port.ask()
        if not debug: debug = questions.debug_mode.ask()
    else:
        if not host: host = "127.0.0.1"
        if not port: port = 8000

    if debug and port == 5173:
        typer.secho(
            "Debug mode is not compatible with port 5173.",
            fg=typer.colors.RED
        )
        raise typer.Exit(1)

    env["APP_NAME"] = name
    env["SERVER_HOST"] = host
    env["SERVER_PORT"] = str(port)
    env["IN_EXECUTION"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    if debug:
        env["DEBUG_MODE"] = "1"
        env["LOG_LEVEL"] = "debug"
    else:
        env["LOG_LEVEL"] = loglevel

    from .lifecycle import Lifecycle
    from .output import LogService

    lifecycle = Lifecycle()

    with LogService(name) as log_service:
        lifecycle.start(env, project_root, log_service)

        if interactive:
            while True:
                if lifecycle.terminate: break

                typer.echo(f"\nApplication status: {lifecycle.status}")
                opt = questions.menu.ask()

                if opt is None or opt == 6: break
                if opt == 5:
                    os.system("cls" if os.name == "nt" else "clear")
                    continue

                if opt == 0: lifecycle.restart(env, project_root, log_service)
                if opt == 1: lifecycle.stop()
                if opt == 2: lifecycle.start(env, project_root, log_service)

                if opt == 3: log_service.join_log(lifecycle)
                if opt == 4: log_service.clear_logs(lifecycle)
        else:
            log_service.start_stream(lifecycle)

        lifecycle.stop()

    typer.secho("Thank you for playing the game of life... Bye!", bold=True)
