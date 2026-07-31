from pathlib import Path
from datetime import datetime, UTC
from threading import Thread
from codecs import getincrementaldecoder
import typer, time

from .helpers import read_key, console_encoding


class LogService:
    def __init__(self, app_name):
        self.streaming = False
        self._pump = None

        log_dir = Path("logs") / app_name
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = log_dir
        self.log_file = log_dir / f"{datetime.now(UTC).strftime('%Y-%m-%d_%H-%M-%S')}.log"
        self.log = None

    def __enter__(self):
        self.log = open(self.log_file, "w", buffering=1)
        return self

    def __exit__(self, *args):
        self.drain()
        if self.log is not None:
            self.log.close()
        return False

    def _stream_log(self, lifecycle):
        proc = lifecycle.proc
        if proc is None or proc.stdout is None: return

        decode = getincrementaldecoder(console_encoding())("backslashreplace").decode

        while True:
            chunk = proc.stdout.read1(8192)
            if not chunk: break

            text = decode(chunk)
            if self.streaming: typer.echo(text, nl=False)

    def _pump_log(self, lifecycle):
        if self._pump is not None and self._pump.is_alive(): return

        self._pump = Thread(target=self._stream_log, daemon=True, args=(lifecycle,))
        self._pump.start()

    def drain(self, timeout=10):
        if self._pump is None: return

        self._pump.join(timeout)
        self._pump = None
        self.streaming = False

    def start_stream(self, lifecycle):
        proc = lifecycle.proc
        if proc is None: return

        self.streaming = True
        self._pump_log(lifecycle)

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
        self._pump_log(lifecycle)

        while proc.poll() is None:
            if read_key() == '\x1b': break

        self.streaming = False

    def clear_logs(self):
        for f in self.log_dir.iterdir():
            if f.is_file() and f != self.log_file: f.unlink(True)
