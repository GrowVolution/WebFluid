import os, platform, typer, subprocess

from webfluid.core.constants import EXECUTION
from webfluid.surface import dist
from webfluid.surface.src import tailwind_cli
from webfluid.utils.cli import download_file
from webfluid.exceptions import TailwindError


def _get_cli_data():
    selector = platform.system().lower()

    machine = platform.machine().lower()
    arch = "x64" if machine == "x86_64" or machine == "amd64" else "arm64"

    if selector != "windows":
        return tailwind_cli[selector].format(architecture=arch), selector
    elif arch == "arm64":
        raise TailwindError("ARM Architecture is not supported on Windows.")
    return tailwind_cli[selector], selector


def _tailwind_cmd():
    tw = "tailwind"
    if os.name == "nt":
        tw += ".exe"

    executable = dist / tw
    if not executable.exists():
        raise TailwindError("Missing tailwind cli executable.")

    return str(executable)


def tailwind_cmd(args, cwd=os.getcwd(), **kwargs):
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

    if not EXECUTION: typer.echo(result.stdout or result.stderr)


def generate_asset(in_file, out_file, cwd):
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


def generate_tailwind_css(fluid):
    from webfluid.core.constants import FRAMEWORK_ROOT, THEMES
    d =  (FRAMEWORK_ROOT / "fluid" / "static" / "css")

    raw_filename = f"tailwind{'_raw' if THEMES else '_no_themes'}.css"

    generate_asset(
        d / raw_filename,
        d / "tailwind.css",
        d
    )

    for d in fluid.project_root.rglob("static/css"):
        in_file = d / raw_filename
        if not in_file.exists(): continue
        generate_asset(
            in_file,
            d / "tailwind.css",
            d
        )


def load_tailwind():
    data = _get_cli_data()
    file_type = ".exe" if data[1] == "windows" else ""

    dest = dist / f"tailwind{file_type}"

    if dest.exists(): return

    download_file(data[0], dest)
    if not dest.exists():
        raise TailwindError("Failed to download standalone tailwind cli.")

    if os.name != "nt": subprocess.run(["chmod", "+x", str(dest)])


def tailwind(ctx: typer.Context):
    if not ctx.args:
        typer.echo(typer.style("Usage: wf tailwind -- [args]", bold=True))
        raise typer.Exit(1)

    tailwind_cmd(ctx.args)


def cli_entry(app):
    app.command(
        context_settings={
            "allow_extra_args": True,
            "ignore_unknown_options": True,
        }
    )(tailwind)
