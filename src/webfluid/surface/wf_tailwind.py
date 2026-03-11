from tqdm import tqdm
from typing import TYPE_CHECKING, Callable
import os, platform, typer, requests, subprocess

from webfluid.surface import dist
from webfluid.exceptions import TailwindError

if TYPE_CHECKING:
    from pathlib import Path
    from webfluid import Fluid

tailwind_cli = {
    "linux": "https://github.com/tailwindlabs/tailwindcss/releases/download/v4.1.18/tailwindcss-linux-{architecture}",
    "windows": "https://github.com/tailwindlabs/tailwindcss/releases/download/v4.1.18/tailwindcss-windows-x64.exe",
    "darwin": "https://github.com/tailwindlabs/tailwindcss/releases/download/v4.1.18/tailwindcss-macos-{architecture}"
}


def _get_cli_data():
    selector = platform.system().lower()

    machine = platform.machine().lower()
    arch = "x64" if machine == "x86_64" or machine == "amd64" else "arm64"

    if selector != "windows":
        return tailwind_cli[selector].format(architecture=arch), selector
    elif arch == "arm64":
        raise TailwindError("ARM Architecture is not supported on Windows.")
    return tailwind_cli[selector], selector


def _tailwind_cmd() -> str:
    tw = "tailwind"
    if os.name == "nt":
        tw += ".exe"

    executable = dist / tw
    if not executable.exists():
        raise TailwindError("Missing tailwind cli executable.")

    return str(executable)


def generate_asset(in_file: "Path", out_file: "Path", cwd: "Path"):
    result = subprocess.run(
        [_tailwind_cmd(),
         "-i", str(in_file),
         "-o", str(out_file),
         "--cwd", str(cwd),
         "--minify"],
        cwd=cwd
    )
    if result.returncode != 0:
        raise TailwindError(f"Failed to generate {out_file}")


def generate_tailwind_css(fluid: "Fluid"):
    out =  (dist.parent / "app" / "static" / "css" / "tailwind.css")

    generate_asset(
        out.parent / "tailwind_raw.css",
        out,
        dist.parent
    )

    for d in fluid.app_root.rglob("static/css"):
        in_file = d / "tailwind_raw.css"
        if not in_file.exists(): continue
        generate_asset(
            in_file,
            d / "tailwind.css",
            d
        )


def load_tailwind(download_fn: Callable):
    data = _get_cli_data()
    file_type = ".exe" if data[1] == "windows" else ""
    dest = dist / f"tailwind{file_type}"

    if dest.exists():
        return

    download_fn(data[0], dest)
    if not dest.exists():
        raise TailwindError("Failed to download standalone tailwind cli.")

    if os.name != "nt":
        os.system(f"chmod +x {str(dest)}")

    typer.echo(typer.style(f"Tailwind successfully setup.", fg=typer.colors.GREEN, bold=True))


def tailwind(ctx: typer.Context):
    if not ctx.args:
        typer.echo(typer.style("Usage: wf tailwind -- [args]", bold=True))
        raise typer.Exit(1)

    args = ctx.args[0:]

    result = subprocess.run(
        [_tailwind_cmd(), *args],
        cwd=os.getcwd()
    )

    if result.returncode != 0:
        raise TailwindError("Tailwind command failed.")

    typer.echo(result.stdout)


def cli_entry(app: typer.Typer):
    app.command(
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
        }
    )(tailwind)
