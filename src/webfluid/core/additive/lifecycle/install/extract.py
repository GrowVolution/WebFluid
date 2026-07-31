from pathlib import Path
import typer

from webfluid.core.identity import FRAMEWORK_ID


def extract(additive):
    extract_path = Path(additive.root_path) / "extract"

    def for_dir(path, name):
        for file in (path / name).rglob("*"):
            if not file.is_file():
                continue

            rel = file.relative_to(path)
            dst = Path.cwd() / FRAMEWORK_ID / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                typer.echo(typer.style(
                    f"[{additive.name}] Could not extract '{'/'.join(rel.parts)}': "
                    "File already exists.", fg=typer.colors.YELLOW
                ))
                continue

            typer.echo(f"[{additive.name}] Extracting '{'/'.join(rel.parts)}'.")

            dst.write_bytes(
                file.read_bytes()
            )

    for_dir(extract_path, "static")
    for_dir(extract_path, "templates")

    typer.echo(typer.style(
        f"[{additive.name}] Finished extracting additives extract files to main app.",
        fg=typer.colors.GREEN, bold=True
    ))
