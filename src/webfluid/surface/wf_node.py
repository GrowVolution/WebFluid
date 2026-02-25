from tqdm import tqdm
import os, platform, requests, typer, subprocess

from webfluid.surface import dist
from webfluid.exceptions import NodeError

node_standalone = {
    "linux": "https://nodejs.org/dist/v24.13.1/node-v24.13.1-linux-{architecture}.tar.xz",
    "windows": "https://nodejs.org/dist/v24.13.1/node-v24.13.1-win-{architecture}.zip",
    "darwin": "https://nodejs.org/dist/v24.13.1/node-v24.13.1-darwin-{architecture}.tar.gz"
}


def _sys_node() -> tuple[bool, str]:
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


def _node_cmd(cmd: str) -> str:
    node = dist / "node"
    if not node.exists():
        if not _sys_node()[0]:
            raise NodeError("Missing node installation / integration... Try running 'fpp init' inside a project directory.")
        return cmd

    if os.name == "nt":
        return str(node / f"{cmd}.cmd")
    return str(node / "bin" / cmd)


def _node_env() -> dict:
    env = os.environ.copy()
    if os.name != "nt":
        node_bin = str(dist / "node" / "bin")
        env["PATH"] = node_bin + os.pathsep + env.get("PATH", "")
    else:
        node_dir = str(dist / "node")
        env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")
    return env


def load_node():
    sys_node = _sys_node()
    if sys_node[0]:
        typer.echo(f"Node.js version {sys_node[1]} is already installed... Skipping integration.")
        return

    data = _get_node_data()
    file_type = "zip" if data[1] == "windows" else (
        "tar.xz" if data[1] == "linux" else "tar.gz")
    dest = dist / f"node.{file_type}"
    bin_folder = dist / "node"

    if bin_folder.exists():
        return

    typer.echo(typer.style(f"Downloading {data[0]}...", bold=True))
    with requests.get(data[0], stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
                total=total, unit="B", unit_scale=True, desc=str(dest)
        ) as bar:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))

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
        typer.echo(typer.style("Usage: wf node <command> [args]", bold=True, fg=typer.colors.YELLOW))
        raise typer.Exit(1)

    command = ctx.args[0]
    args = ctx.args[1:]

    result = subprocess.run(
        [_node_cmd(command), *args],
        cwd=os.getcwd(),
        env=_node_env()
    )

    if result.returncode != 0:
        raise NodeError("Node command execution failed.")


def cli_entry(app: typer.Typer):
    app.command(
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
        }
    )(node)
