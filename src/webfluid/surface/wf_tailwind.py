from typing import TYPE_CHECKING, Callable
import os, platform, typer, subprocess

from webfluid.surface import dist
from webfluid.exceptions import TailwindError

if TYPE_CHECKING:
    from pathlib import Path
    from webfluid.core.fluid import Fluid

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


def tailwind_cmd(args: list[str], cwd: "Path | str" = os.getcwd(), **kwargs):
    default_kwargs = {
        "cwd": cwd,
        "capture_output": True,
        "text": True
    }

    result = subprocess.run(
        [_tailwind_cmd(), *args],
        **(kwargs | default_kwargs)
    )

    if result.returncode != 0:
        raise TailwindError(result.stderr or result.stdout)


def generate_asset(in_file: "Path", out_file: "Path", cwd: "Path"):
    if not in_file.exists(): return

    tailwind_cmd(
        [
            "-i", str(in_file),
            "-o", str(out_file),
            "--cwd", str(cwd),
            "--minify"
        ],
        cwd
    )


def generate_themes(fluid: "Fluid"):
    from webfluid.core.constants import FRAMEWORK_ROOT
    d =  (FRAMEWORK_ROOT / "fluid" / "static" / "css")

    generate_asset(
        d / "theme_raw.css",
        d / "theme.css",
        FRAMEWORK_ROOT
    )

    for d in fluid.app_root.rglob("static/css"):
        in_file = d / "theme_raw.css"
        if not in_file.exists(): continue
        generate_asset(
            in_file,
            d / "theme.css",
            d
        )


def generate_tailwind_css(fluid: "Fluid"):
    from webfluid.core.constants import FRAMEWORK_ROOT, THEMES
    d =  (FRAMEWORK_ROOT / "fluid" / "static" / "css")

    if THEMES: target = d / "tailwind_themeless.css"
    else: target = d / "tailwind_raw.css"

    generate_asset(
        target,
        d / "tailwind.css",
        FRAMEWORK_ROOT
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

    if dest.exists(): return

    download_fn(data[0], dest)
    if not dest.exists():
        raise TailwindError("Failed to download standalone tailwind cli.")

    if os.name != "nt": os.system(f"chmod +x {str(dest)}")


def tailwind(ctx: typer.Context):
    if not ctx.args:
        typer.echo(typer.style("Usage: wf tailwind -- [args]", bold=True))
        raise typer.Exit(1)

    tailwind_cmd(ctx.args)


def cli_entry(app: typer.Typer):
    app.command(
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
        }
    )(tailwind)
