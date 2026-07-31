import os, subprocess, signal

from webfluid.surface.wf_node import node_proc


proc = None
dev_server = "http://localhost:5173"
dev_prefix = "/vite-dev"


def stop():
    if proc is None or proc.poll() is not None:
        return

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        proc.wait()
    else:
        os.killpg(proc.pid, signal.SIGINT)

        try: proc.wait(0.5)
        except subprocess.TimeoutExpired:
            pass

        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()


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

    add_proxy(
        fluid, dev_server,
        prefix=dev_prefix,
        pass_prefix=True
    )
    fluid.shutdown_hook(stop)
    return wrapped
