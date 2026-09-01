import os, platform, typer, subprocess

from webfluid.core.constants import EXECUTION
from webfluid.core.identity import CLI_NAME
from webfluid.surface import dist
from webfluid.surface.src import node_standalone
from webfluid.utils.cli import download_file
from webfluid.exceptions import NodeError


def _sys_node():
    try:
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True
        )
    except FileNotFoundError:
        return False, ""
    return result.returncode == 0, result.stdout or ""


def _get_node_data():
    selector = platform.system().lower()

    machine = platform.machine().lower()
    arch = "x64" if machine == "x86_64" or machine == "amd64" else "arm64"

    return node_standalone[selector].format(architecture=arch), selector


def _node_cmd(cmd):
    node = dist / "node"
    if not node.exists():
        if not _sys_node()[0]:
            raise NodeError("Missing node installation / integration... "
                            f"Try running '{CLI_NAME} create project dummy -sd'.")
        return cmd

    if os.name == "nt":
        if cmd != "node":
            return str(node / f"{cmd}.cmd")
        return str(node / f"{cmd}.exe")
    return str(node / "bin" / cmd)


def _node_env():
    env = os.environ.copy()
    if os.name != "nt":
        node_bin = str(dist / "node" / "bin")
        env["PATH"] = node_bin + os.pathsep + env.get("PATH", "")
    else:
        node_dir = str(dist / "node")
        env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")
    return env


def node_cmd(cmd, cwd=os.getcwd(), **kwargs):
    default_kwargs = {
        "cwd": cwd,
        "env": _node_env(),
        "capture_output": True,
        "text": True
    }

    result = subprocess.run(
        [_node_cmd(cmd[0]), *cmd[1:]],
        **(kwargs | default_kwargs)
    )

    if result.returncode != 0:
        raise NodeError(result.stderr or result.stdout)

    if not EXECUTION: typer.echo(result.stdout or result.stderr)


_job = None


def _build_job():
    import ctypes
    from ctypes import wintypes

    class _IoCounters(ctypes.Structure):
        _fields_ = [(field, ctypes.c_ulonglong) for field in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount"
        )]

    class _BasicLimits(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
            ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD)
        ]

    class _ExtendedLimits(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BasicLimits),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t)
        ]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    k32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD
    ]
    k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]

    handle = k32.CreateJobObjectW(None, None)
    if not handle: return None

    limits = _ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = 0x2000
    if not k32.SetInformationJobObject(
            handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
    ): return None

    return k32, handle


def _bind_lifetime(proc):
    global _job
    if _job is None:
        try: _job = _build_job() or False
        except OSError: _job = False

    if not _job: return
    try: _job[0].AssignProcessToJobObject(_job[1], int(proc._handle))
    except OSError: pass


def node_proc(cmd, cwd=os.getcwd(), **kwargs):
    flags = 0
    if os.name == "nt":
        flags = (
            subprocess.CREATE_NEW_PROCESS_GROUP |
            subprocess.CREATE_NO_WINDOW
        )
    default_kwargs = {
        "cwd": cwd,
        "env": _node_env(),
        "stdin": subprocess.DEVNULL,
        "creationflags": flags
    }
    proc = subprocess.Popen(
        [_node_cmd(cmd[0]), *cmd[1:]],
        **(kwargs | default_kwargs)
    )

    if os.name == "nt": _bind_lifetime(proc)
    return proc


def load_node():
    sys_node = _sys_node()
    if sys_node[0]:
        typer.echo(f"Node.js version {sys_node[1]} is already installed... Skipping integration.")
        return

    data = _get_node_data()
    file_type = "zip" if data[1] == "windows" else (
        "tar.xz" if data[1] == "linux" else "tar.gz")

    from webfluid.surface import dist
    dest = dist / f"node.{file_type}"
    bin_folder = dist / "node"

    if bin_folder.exists():
        return

    download_file(data[0], dest)
    if not dest.exists():
        raise NodeError("Failed to download standalone node bundle.")

    typer.echo(typer.style(f"Extracting node.{file_type}...", bold=True))

    if file_type == "zip":
        import zipfile
        with zipfile.ZipFile(dest, "r") as f:
            f.extractall(dist)
    else:
        import tarfile
        with tarfile.open(dest, "r") as f:
            f.extractall(dist)

    extracted_folder = dist / data[0].split("/")[-1].removesuffix(f".{file_type}")
    extracted_folder.rename(bin_folder)

    dest.unlink()


def node(ctx: typer.Context):
    if not ctx.args:
        typer.echo(typer.style(f"Usage: {CLI_NAME} node <command> [args]",
                               bold=True, fg=typer.colors.YELLOW))
        raise typer.Exit(1)

    node_cmd(ctx.args)


def cli_entry(app):
    app.command(
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
        }
    )(node)
