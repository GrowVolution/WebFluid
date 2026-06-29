from pathlib import Path
import json, tomllib, typer

from webfluid.cli import questions
from webfluid.cli.ocean.archive import build_archive, sha256_hex
from webfluid.utils.ocean import Ocean, humanize_error
from webfluid.exceptions import OceanError


def _detect_package(root: Path) -> tuple[str | None, str | None]:
    manifest = root / "manifest.json"
    if manifest.exists():
        try: data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError: return "additives", None
        return "additives", data.get("id")

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try: data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError: return "extensions", None
        return "extensions", data.get("project", {}).get("name")

    return None, None


def _choose_maintainer(status: dict) -> int | None:
    publisher = status.get("publisher")
    orgas = status.get("orgas") or []

    options: list[tuple[str, object]] = []
    if publisher:
        options.append((f"Personal · {publisher.get('name')}", "__personal__"))
    for orga in orgas:
        label = orga.get("name")
        if not orga.get("stripe", {}).get("onboarded"):
            label += " (not onboarded)"
        options.append((label, orga["id"]))

    if not options:
        typer.secho(
            "You are not enrolled as a publisher or organisation. "
            "Enroll on the Ocean first.",
            fg=typer.colors.RED
        )
        raise typer.Exit(1)

    if len(options) == 1:
        value = options[0][1]
    else:
        value = questions.ocean_maintainer(options).ask()
        if value is None:
            typer.secho("Aborted.", fg=typer.colors.YELLOW)
            raise typer.Exit()

    return None if value == "__personal__" else value


def _choose_price(ptype: str) -> float | None:
    answer = questions.ocean_price(ptype == "extensions").ask()
    if answer is None:
        typer.secho("Aborted.", fg=typer.colors.YELLOW)
        raise typer.Exit()
    answer = answer.strip()
    return float(answer) if answer else None


def _select_license(ocean: Ocean, ptype: str, package_id: str):
    typer.secho("This package has no license yet. Let's pick one.", bold=True)

    license_id = None
    while license_id is None:
        query = questions.ocean_license_query.ask()
        if query is None:
            typer.secho("Skipped license selection.", fg=typer.colors.YELLOW)
            return

        try: matches = ocean.license_search(query)
        except OceanError as e:
            typer.secho(f"License search failed: {humanize_error(e.detail)}",
                        fg=typer.colors.RED)
            continue
        if not matches:
            typer.secho("No licenses found. Try another query.",
                        fg=typer.colors.YELLOW)
            continue

        choice = questions.ocean_license_choice(matches[:10]).ask()
        if choice is None:
            typer.secho("Skipped license selection.", fg=typer.colors.YELLOW)
            return
        if choice == "__search__": continue
        license_id = choice

    try:
        fields = ocean.license_placeholders(ptype, package_id, license_id)
    except OceanError as e:
        typer.secho(f"Could not load license fields: {humanize_error(e.detail)}",
                    fg=typer.colors.RED)
        return

    values = {}
    for field in fields.get("fields", []):
        default = field.get("default", "")
        answer = questions.text(f"{field['label']}:", default=default).ask()
        values[field["placeholder"]] = answer if answer is not None else default

    try:
        ocean.select_license(ptype, package_id, license_id, values)
        typer.secho(f"License '{license_id}' applied.", fg=typer.colors.GREEN)
    except OceanError as e:
        typer.secho(f"Could not apply license: {humanize_error(e.detail)}",
                    fg=typer.colors.RED)


def publish():
    project_root = Path.cwd()
    ocean = Ocean()
    if not ocean.authenticated:
        typer.secho("Publishing requires login. Run 'wf ocean login' first.",
                    fg=typer.colors.RED)
        raise typer.Exit(1)

    ptype, package_id = _detect_package(project_root)
    if ptype is None:
        typer.secho(
            "No package found. Expected a manifest.json (additive) "
            "or pyproject.toml (extension) in the current directory.",
            fg=typer.colors.RED
        )
        raise typer.Exit(1)
    if not package_id:
        typer.secho(
            "No package id assigned. Set an id in your "
            f"{'manifest.json' if ptype == 'additives' else 'pyproject.toml'} "
            "before publishing.",
            fg=typer.colors.RED
        )
        raise typer.Exit(1)

    typer.secho(f"Publishing {ptype[:-1]} '{package_id}'...", bold=True)

    try:
        status = ocean.maintainers()
    except OceanError as e:
        typer.secho(
            f"Could not load your maintainer accounts: {humanize_error(e.detail)}",
            fg=typer.colors.RED
        )
        raise typer.Exit(1)

    orga = _choose_maintainer(status)
    price = _choose_price(ptype)

    typer.secho("Building package archive...", bold=True)
    data = build_archive(project_root)
    checksum = sha256_hex(data)

    try:
        pkg = ocean.publish(ptype, data, checksum, orga=orga, price=price)
    except OceanError as e:
        typer.secho(f"Publish failed: {humanize_error(e.detail)}",
                    fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Published '{pkg['id']}'.", fg=typer.colors.GREEN, bold=True)

    if pkg.get("license_missing"):
        _select_license(ocean, ptype, pkg["id"])
