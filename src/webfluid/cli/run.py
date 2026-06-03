from configparser import ConfigParser
from pathlib import Path
from datetime import datetime, UTC
from threading import Thread
import typer, subprocess, sys, os, signal, time

from webfluid.cli import questions

_proc: subprocess.Popen | None = None
_streaming = False
_terminate = False
_log = None


def _env_from_config(config_file: Path, debug: bool) -> dict:
    env = os.environ.copy()
    cfg = ConfigParser()
    cfg.optionxform = str
    cfg.read(config_file)
    for k, v in cfg.defaults().items():
        env[k] = v
    for section in cfg.sections():
        if section == "dev" and not debug:
            continue
        for k, v in cfg[section].items():
            env[k] = v
    return env


def _read_key() -> str:
    if os.name == "nt":
        import msvcrt
        c = msvcrt.getch()
        if c == '' or c == 'à':
            c = msvcrt.getch()
        return c.decode()

    import termios, tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    return key


def _exit(signum: int, _):
    typer.secho(f"Handling signal {'SIGINT' if signum == signal.SIGINT else 'SIGTERM'}, "
                 "shutting down...", fg=typer.colors.YELLOW)
    global _terminate
    _terminate = True


def _stream_log():
    if _proc is None or _proc.stdout is None: return

    while _streaming:
        line = _proc.stdout.readline()
        if not _streaming: break
        if line: typer.echo(line, nl=False)


def _join_log():
    if _proc is None: return

    typer.secho("Joining application log...", bold=True)
    typer.secho("Press STRG+Q to return to menu.\n", fg=typer.colors.YELLOW)
    time.sleep(1)

    global _streaming
    _streaming = True
    Thread(target=_stream_log, daemon=True).start()

    while _proc.poll() is None:
        if _read_key() == "\x11": break

    _streaming = False


def _start(env: dict, project_root: Path):
    global _proc
    if _proc and _proc.poll() is None:
        typer.secho("Application already running.", fg=typer.colors.YELLOW)
        return

    typer.secho("Starting application...", fg=typer.colors.GREEN)
    _proc = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=_log,
        env=env,
        cwd=project_root,
        text=True,
        bufsize=1
    )


def _stop():
    if _proc is None:
        typer.secho("Application not running.", fg=typer.colors.YELLOW)
        return

    if _proc.poll() is None:
        typer.secho("Stopping application...", fg=typer.colors.RED)
        _proc.terminate()
        _proc.wait()


def _restart(env: dict, project_root: Path):
    _stop()
    _start(env, project_root)


def _status() -> str:
    running = _proc and _proc.poll() is None
    status = "Running" if running else "Stopped"

    if running: return typer.style(status, fg=typer.colors.GREEN)
    return typer.style(status, fg=typer.colors.RED)


def _clear_logs(log_dir: Path):
    log_files = sorted(
        [f for f in log_dir.iterdir() if f.is_file()],
        key=lambda f: f.stat().st_mtime
    )
    if not log_files: return

    running = _proc and _proc.poll() is None
    to_delete = log_files[:-1] if running else log_files
    for f in to_delete: f.unlink(True)


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

    global _proc, _streaming, _log
    log_dir = Path("logs") / name
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{datetime.now(UTC).strftime('%Y-%m-%d_%H-%M-%S')}.log"

    env = _env_from_config(config_file, debug)
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
    env["LOG_LEVEL"] = loglevel
    env["PYTHONUNBUFFERED"] = "1"
    if debug: env["DEBUG_MODE"] = "1"

    _log = open(log_file, "w", buffering=1)
    _start(env, project_root)

    signal.signal(signal.SIGINT, _exit)
    signal.signal(signal.SIGTERM, _exit)

    if interactive:
        # TODO: Fix process management on Windows

        while True:
            if _terminate: break

            typer.echo(f"\nApplication status: {_status()}")
            opt = questions.menu.ask()

            if opt == 6: break
            if opt == 5:
                os.system("cls" if os.name == "nt" else "clear")
                continue

            if opt == 0: _restart(env, project_root)
            if opt == 1: _stop()
            if opt == 2: _start(env, project_root)

            if opt == 3: _join_log()
            if opt == 4: _clear_logs(log_dir)
    else:
        _streaming = True
        Thread(target=_stream_log, daemon=True).start()

        while _proc.poll() is None:
            time.sleep(0.05)
            if _terminate: break

        _streaming = False

    _stop()
    _log.close()

    typer.secho("Thank you for playing the game of life... Bye!", bold=True)


def cli_entry(app: typer.Typer):
    app.command()(run)
