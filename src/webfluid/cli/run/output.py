from pathlib import Path
from datetime import datetime, UTC
from threading import Thread
import typer, time

from .helpers import read_key


class LogService:
    def __init__(self, app_name):
        self.streaming = False

        log_dir = Path("logs") / app_name
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = log_dir
        self.log_file = log_dir / f"{datetime.now(UTC).strftime('%Y-%m-%d_%H-%M-%S')}.log"
        self.log = None

    def __enter__(self):
        self.log = open(self.log_file, "w", buffering=1)
        return self

    def __exit__(self, *args):
        if self.log is not None:
            self.log.close()
        return False

    def _stream_log(self, lifecycle):
        proc = lifecycle.proc
        if proc is None or proc.stdout is None: return

        while self.streaming:
            if proc is None: break
            line = proc.stdout.readline()
            if not self.streaming: break
            if line: typer.echo(line, nl=False)

    def start_stream(self, lifecycle):
        proc = lifecycle.proc
        if proc is None: return

        self.streaming = True
        Thread(target=self._stream_log, daemon=True, args=(lifecycle,)).start()

        while proc.poll() is None:
            time.sleep(0.05)
            if lifecycle.terminate: break

    def join_log(self, lifecycle):
        proc = lifecycle.proc
        if proc is None: return

        typer.secho("Joining application log...", bold=True)
        typer.secho("Press ESC to return to menu.\n", fg=typer.colors.YELLOW)
        time.sleep(1)

        self.streaming = True
        Thread(target=self._stream_log, daemon=True, args=(lifecycle,)).start()

        while proc.poll() is None:
            if read_key() == '\x1b': break

        self.streaming = False

    def clear_logs(self, lifecycle):
        log_files = sorted(
            [f for f in self.log_dir.iterdir() if f.is_file()],
            key=lambda f: f.stat().st_mtime
        )
        if not log_files: return

        proc = lifecycle.proc
        running = proc and proc.poll() is None
        to_delete = log_files[:-1] if running else log_files
        for f in to_delete: f.unlink(True)
