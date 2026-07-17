import typer, sys, subprocess


def install_packages(additive):
    if not "requires" in additive.manifest: return
    requirements = additive.manifest["requires"]
    if not "packages" in requirements: return

    packages = requirements["packages"]
    if not isinstance(packages, list):
        typer.echo(typer.style(
            f"[{additive.name}] Invalid packages requirement type: {type(packages)}",
            fg=typer.colors.YELLOW, bold=True
        ))
        return

    for package in packages:
        typer.echo(f"[{additive.name}] Installing required package '{package}'...")

        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", package],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            typer.echo(typer.style(
                f"[{additive.name}] Failed to install package '{package}': {result.stderr}",
                fg=typer.colors.RED, bold=True
            ))
