import os, subprocess, signal, atexit, time

from webfluid.core.constants import EXT_SCHEDULING
from webfluid.surface.wf_node import node_proc
from webfluid.utils.logging import factory as log_factory


proc = None
root = None
started = 0.0
failures = 0
stopping = False
dev_server = "http://localhost:5173"
dev_prefix = "/vite-dev"
watch_job = "webfluid_vite_watchdog"
watch_interval = 5
quick_exit = 15
max_failures = 5


def start():
    global proc, started
    proc = node_proc(
        ["node", "node_modules/vite/bin/vite.js"],
        root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    started = time.monotonic()


def watch():
    global failures
    current = proc
    if stopping or current is None or current.poll() is None: return
    if failures >= max_failures: return

    failures = failures + 1 if time.monotonic() - started < quick_exit else 1
    if failures >= max_failures:
        log_factory.warning(
            f"The Vite dev server stopped {failures} times in a row right after starting "
            f"(exit code {current.returncode}). It is no longer restarted; run "
            f"'node node_modules/vite/bin/vite.js' in the project root to see why."
        )
        return

    log_factory.warning(f"The Vite dev server stopped (exit code {current.returncode}). Restarting it.")
    start()


def stop():
    global proc, stopping
    stopping = True
    if proc is None: return

    current, proc = proc, None
    if current.poll() is not None: return

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(current.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        current.wait()
    else:
        os.killpg(current.pid, signal.SIGINT)

        try: current.wait(0.5)
        except subprocess.TimeoutExpired:
            pass

        if current.poll() is None:
            os.killpg(current.pid, signal.SIGKILL)
            current.wait()


def supervise():
    if not EXT_SCHEDULING:
        log_factory.warning(
            "The Vite dev server runs unsupervised because EXT_SCHEDULING is off. If it stops, "
            "frontend requests fail silently until you restart the app."
        )
        return

    from apscheduler.triggers.interval import IntervalTrigger
    from webfluid.core.ext import scheduler
    scheduler.add_job(
        watch, IntervalTrigger(seconds=watch_interval), id=watch_job,
        replace_existing=True, max_instances=1, coalesce=True, misfire_grace_time=None
    )


def startup_hook(fluid):
    from webfluid.utils.core import add_proxy

    def wrapped():
        global root, stopping, failures
        root, stopping, failures = fluid.project_root, False, 0
        start()
        atexit.register(stop)
        supervise()

    add_proxy(
        fluid, dev_server,
        prefix=dev_prefix,
        pass_prefix=True
    )
    fluid.shutdown_hook(stop)
    return wrapped
