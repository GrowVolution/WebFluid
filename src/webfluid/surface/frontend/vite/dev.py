import os, subprocess, signal, atexit

from webfluid.surface.wf_node import node_proc


proc = None
dev_server = "http://localhost:5173"
dev_prefix = "/vite-dev"


def stop():
    global proc
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


def startup_hook(fluid):
    from webfluid.utils.core import add_proxy

    def wrapped():
        global proc

        proc = node_proc(
            ["node", "node_modules/vite/bin/vite.js"],
            fluid.project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        atexit.register(stop)

    add_proxy(
        fluid, dev_server,
        prefix=dev_prefix,
        pass_prefix=True
    )
    fluid.shutdown_hook(stop)
    return wrapped
