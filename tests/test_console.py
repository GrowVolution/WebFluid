from contextlib import ExitStack
from threading import Thread
from tqdm import tqdm
import logging, os, signal, sys, pytest

from webfluid.cli.run.helpers import console_encoding, env_from_config
from webfluid.cli.run.lifecycle import Lifecycle
from webfluid.cli.run.output import LogService
from webfluid.utils.cli import progress_bar
from webfluid.utils.logging import factory as log_factory

FRAMES = """
import sys, time
for i in range(4):
    sys.stdout.buffer.write(f"\\rframe {i}".encode())
    sys.stdout.buffer.flush()
    time.sleep(0.05)
sys.stdout.buffer.write(b"\\ndone\\n")
"""

WIDE = """
import sys
sys.stdout.buffer.write(("\\u2713" * 4000).encode())
"""

RUNNING = "import time; time.sleep(30)"

SHUTDOWN = """
import sys, time
sys.stdout.buffer.write(b"running")
sys.stdout.buffer.flush()
time.sleep(0.4)
sys.stdout.buffer.write(b"shutting down")
"""


class Running:
    def __init__(self, service, lifecycle, env, root, written):
        self.service = service
        self.lifecycle = lifecycle
        self.env = env
        self.root = root
        self.written = written

    def close(self):
        self.service.__exit__()
        return "".join(self.written)

    def pump(self, echo=True):
        self.service.streaming = echo
        self.service._pump_log(self.lifecycle)
        thread = self.service._pump
        self.service.drain(15)

        assert not thread.is_alive()
        self.lifecycle.proc.wait(5)
        return "".join(self.written)


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("webfluid.cli.run.output.console_encoding", lambda: "utf-8")

    written = []
    monkeypatch.setattr(
        "webfluid.cli.run.output.typer.echo",
        lambda message, nl=True: written.append(message)
    )
    handlers = signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGTERM)
    stack = ExitStack()
    started = []

    def factory(source):
        (tmp_path / "main.py").write_text(source, encoding="utf-8")
        env = { **os.environ, "PYTHONIOENCODING": "utf-8" }

        service = stack.enter_context(LogService("tests.app"))
        lifecycle = Lifecycle()
        lifecycle.start(env, tmp_path, service)

        started.append(lifecycle)
        return Running(service, lifecycle, env, tmp_path, written)

    yield factory

    for lifecycle in started:
        if lifecycle.proc and lifecycle.proc.poll() is None: lifecycle.proc.kill()
    stack.close()

    signal.signal(signal.SIGINT, handlers[0])
    signal.signal(signal.SIGTERM, handlers[1])


def test_carriage_returns_reach_the_console_unchanged(app):
    assert app(FRAMES).pump() == "\rframe 0\rframe 1\rframe 2\rframe 3\ndone\n"


def test_progress_frames_are_forwarded_while_the_app_runs(app):
    running = app(FRAMES)
    running.pump()

    assert len(running.written) > 1


def test_characters_split_across_reads_stay_intact(app):
    assert app(WIDE).pump() == "✓" * 4000


def test_a_silenced_stream_keeps_draining_the_pipe(app):
    running = app(WIDE)

    assert running.pump(echo=False) == ""
    assert running.lifecycle.proc.poll() == 0


def test_the_non_interactive_run_streams_until_the_app_exits(app):
    running = app("import sys; sys.stdout.write('up')")

    running.service.start_stream(running.lifecycle)
    running.service.drain()

    assert "".join(running.written) == "up"
    assert running.lifecycle.proc.poll() == 0


def test_shutdown_output_still_reaches_the_console(app):
    running = app(SHUTDOWN)
    running.lifecycle.terminate = True

    running.service.start_stream(running.lifecycle)

    assert running.close() == "runningshutting down"


def test_stopping_ends_a_running_app(app):
    running = app(RUNNING)
    proc = running.lifecycle.proc

    assert "Running" in running.lifecycle.status

    running.lifecycle.stop()

    assert running.lifecycle.proc is None
    assert proc.poll() is not None
    assert "Stopped" in running.lifecycle.status


def test_restarting_replaces_the_process(app):
    running = app(RUNNING)
    first = running.lifecycle.proc

    running.lifecycle.restart(running.env, running.root, running.service)

    assert running.lifecycle.proc is not first
    assert first.poll() is not None
    assert running.lifecycle.proc.poll() is None


def test_console_encoding_falls_back_without_a_stream(monkeypatch):
    monkeypatch.setattr(sys, "stdout", object())
    assert console_encoding() == "utf-8"


def test_clearing_logs_spares_the_open_log_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with LogService("tests.app") as service:
        for name in ("older.log", "newer.log"):
            (service.log_dir / name).write_text("", encoding="utf-8")

        service.clear_logs()

        assert [f.name for f in service.log_dir.iterdir()] == [service.log_file.name]
        assert not service.log.closed

    assert service.log.closed


def test_progress_bar_gets_a_width_without_a_terminal(monkeypatch):
    monkeypatch.setenv("COLUMNS", "120")
    monkeypatch.setenv("LINES", "40")

    with progress_bar("Startup hooks phase", 2) as bar:
        assert bar.ncols == 119

    with progress_bar("Startup hooks phase", 2, ncols=42) as bar:
        assert bar.ncols == 42


def test_log_records_are_written_through_the_active_bar(monkeypatch):
    record = logging.LogRecord(
        log_factory.adtv_logger, logging.INFO, __file__, 1,
        "Registering: blog", None, None
    )
    written = []
    monkeypatch.setattr(
        tqdm, "write", classmethod(lambda cls, message, **_: written.append(message))
    )

    with progress_bar("Additive registration phase", 1):
        log_factory.colored_console.emit(record)

    assert len(written) == 1
    assert "Registering: blog" in written[0]


def test_log_records_fall_back_to_the_plain_stream(monkeypatch):
    from io import StringIO

    record = logging.LogRecord(
        log_factory.main_logger, logging.INFO, __file__, 1,
        "Server stopped.", None, None
    )
    stream = StringIO()
    monkeypatch.setattr(log_factory.colored_console, "stream", stream)

    log_factory.colored_console.emit(record)

    assert stream.getvalue().startswith("\x1b[")
    assert "Server stopped." in stream.getvalue()
    assert stream.getvalue().endswith("\n")


def test_exceptions_are_logged_with_their_traceback(monkeypatch):
    from io import StringIO

    stream = StringIO()
    monkeypatch.setattr("webfluid.utils.logging.EXECUTION", True)
    monkeypatch.setattr(log_factory.colored_console, "stream", stream)
    monkeypatch.setattr(log_factory.console, "stream", StringIO())

    try:
        log_factory.start_session()
        try: raise RuntimeError("kaputt")
        except RuntimeError as e: log_factory.exception(e, "[Babel] Startup failed.")

        written = stream.getvalue()
    finally:
        for name in (log_factory.main_logger, log_factory.adtv_logger):
            logging.getLogger(name).handlers.clear()

    assert "[ERROR]" in written
    assert "[Babel] Startup failed." in written
    assert "RuntimeError: kaputt" in written
    assert "Traceback (most recent call last):" in written


async def test_the_additive_context_switches_the_logger():
    @log_factory.additive_context
    async def registering(): return log_factory.logger.name

    assert await registering() == log_factory.adtv_logger
    assert log_factory.logger.name == log_factory.main_logger


def test_session_logger_writes_to_console_and_file(monkeypatch):
    monkeypatch.setattr("webfluid.utils.logging.EXECUTION", True)
    monkeypatch.setenv("LOG_LEVEL", "debug")

    try:
        log_factory.start_session()
        logger = logging.getLogger(log_factory.main_logger)

        assert logger.level == logging.DEBUG
        assert logger.propagate is False
        assert logger.handlers == [log_factory.colored_console, log_factory.console]
        assert logging.getLogger(log_factory.adtv_logger).handlers == logger.handlers
    finally:
        for name in (log_factory.main_logger, log_factory.adtv_logger):
            logging.getLogger(name).handlers.clear()


def test_run_exports_the_console_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COLUMNS", "132")
    monkeypatch.setenv("LINES", "50")

    (tmp_path / "main.py").write_text("", encoding="utf-8")
    configs = tmp_path / "app_configs"
    configs.mkdir()
    (configs / "demo.ini").write_text(
        "[DEFAULT]\nSECRET_KEY = s3cret\n\n[additives]\nblog = true\nshop = false\n",
        encoding="utf-8"
    )

    started = {}

    class Lifecycle:
        terminate = False
        def start(self, env, project_root, log_service): started.update(env)
        def stop(self): pass

    class Service:
        def __init__(self, name): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def start_stream(self, lifecycle): pass

    monkeypatch.setattr("webfluid.cli.run.lifecycle.Lifecycle", Lifecycle)
    monkeypatch.setattr("webfluid.cli.run.output.LogService", Service)

    from webfluid.cli.run.main import run
    run("demo", host=None, port=None, loglevel="warning",
        interactive=False, debug=False)

    assert started["APP_NAME"] == "demo"
    assert started["SERVER_HOST"] == "127.0.0.1"
    assert started["SERVER_PORT"] == "8000"
    assert started["IN_EXECUTION"] == "1"
    assert started["LOG_LEVEL"] == "warning"
    assert started["SECRET_KEY"] == "s3cret"
    assert started["ENABLED_ADDITIVES"] == "1"
    assert started["PYTHONUNBUFFERED"] == "1"
    assert started["PYTHONIOENCODING"].endswith(":backslashreplace")
    assert (started["COLUMNS"], started["LINES"]) == ("132", "50")


def test_run_refuses_an_incomplete_project(tmp_path, monkeypatch):
    import typer

    monkeypatch.chdir(tmp_path)
    from webfluid.cli.run.main import run

    with pytest.raises(typer.Exit): run("demo", None, None, "info", False, False)

    configs = tmp_path / "app_configs"
    configs.mkdir()
    (configs / "demo.ini").write_text("[DEFAULT]\n", encoding="utf-8")

    with pytest.raises(typer.Exit): run("demo", None, None, "info", False, False)

    (tmp_path / "main.py").write_text("", encoding="utf-8")
    with pytest.raises(typer.Exit): run("demo", None, 5173, "info", False, True)


def test_debug_mode_forces_debug_logging(tmp_path, monkeypatch):
    configs = tmp_path / "app_configs"
    configs.mkdir()
    (configs / "demo.ini").write_text(
        "[DEFAULT]\nSECRET_KEY = s3cret\n\n[dev]\nDEV_AUTO_INSTALL = 1\n",
        encoding="utf-8"
    )

    assert "DEV_AUTO_INSTALL" not in env_from_config(configs / "demo.ini", False)
    assert env_from_config(configs / "demo.ini", True)["DEV_AUTO_INSTALL"] == "1"
