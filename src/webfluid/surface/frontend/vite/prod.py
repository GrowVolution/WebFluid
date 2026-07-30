import subprocess

from webfluid.core.constants import CHECK_FRONTEND, BUILD_FRONTEND
from webfluid.surface.wf_node import node_proc, node_cmd
from webfluid.utils.core import run_in_executor
from webfluid.exceptions import FrontendException, NodeError

proc = None


def startup_hook(fluid):
    async def wrapped():
        if CHECK_FRONTEND:
            try:
                node_cmd(
                    ["npm", "run", "check", "--workspaces"],
                    fluid.project_root
                )
            except NodeError as e:
                if "No workspaces found!" not in str(e):
                    raise e

        if BUILD_FRONTEND:
            global proc

            proc = node_proc(
                ["npm", "run", "build", "--workspaces"],
                fluid.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            out, err = await run_in_executor(proc.communicate)
            if proc.returncode != 0:
                msg = err or out or "Unknown error"
                if "No workspaces found!" not in msg:
                    raise FrontendException(msg)

    return wrapped
