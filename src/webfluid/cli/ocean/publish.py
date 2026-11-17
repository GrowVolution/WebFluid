from pathlib import Path
import json, tomllib, typer

from webfluid.cli import questions
from webfluid.cli.ocean.archive import build_archive, scan, sha256_hex
from webfluid.core.identity import CLI_NAME, HUB_NAME
from webfluid.exceptions import OceanError
from webfluid.utils.ocean import RESERVED_FILES, Ocean, humanize_error


def _detect_package(root):
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


def _choose_maintainer(status):
    publisher = status.get("publisher")
    orgas = status.get("orgas") or []

    options = []
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
            f"Enroll on the {HUB_NAME} first.",
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


def _choose_price(ptype):
    answer = questions.ocean_price(ptype == "extensions").ask()
    if answer is None:
        typer.secho("Aborted.", fg=typer.colors.YELLOW)
        raise typer.Exit()
    answer = answer.strip()
    return float(answer) if answer else None


def _select_license(ocean, ptype, package_id):
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

    try: fields = ocean.license_placeholders(ptype, package_id, license_id)
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


def _detect_version(root, ptype):
    try:
        if ptype == "additives":
            return str(json.loads((root / "manifest.json").read_text(encoding="utf-8")).get("version") or "") or None
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8")).get("project", {})
        return str(project.get("version") or "") or None
    except (OSError, json.JSONDecodeError, tomllib.TOMLDecodeError):
        return None


def _existing(ocean, ptype, package_id):
    try: return ocean.package(ptype, package_id)
    except OceanError as e:
        if e.status == 404: return None
        typer.secho(f"Could not look up '{package_id}': {humanize_error(e.detail)}", fg=typer.colors.RED)
        raise typer.Exit(1)


def _report_skipped(sensitive, links):
    if sensitive:
        typer.secho(
            f"Left out {len(sensitive)} file(s) that look like secrets or local data: {', '.join(sensitive)}. "
            "Add them to .gitignore to silence this notice.",
            fg=typer.colors.YELLOW
        )
    if links:
        typer.secho(f"Left out symbolic links, which are never followed: {', '.join(links)}.",
                    fg=typer.colors.YELLOW)


def _review_notice(package):
    if package.get("review_status") in ("pending", "changes_requested"):
        typer.secho(
            f"The first release of a paid package is reviewed by the {HUB_NAME} before it is offered. "
            "You will be notified about the decision.",
            fg=typer.colors.YELLOW
        )


def _release(ocean, ptype, package_id, package, data, checksum, version, security):
    if "publish" not in (package.get("actions") or []):
        typer.secho(f"'{package_id}' exists and you may not publish releases of it.", fg=typer.colors.RED)
        raise typer.Exit(1)
    known = {release.get("version") for release in package.get("releases") or []}
    if version and version in known:
        typer.secho(f"Version {version} of '{package_id}' exists already. Raise the version first.",
                    fg=typer.colors.RED)
        raise typer.Exit(1)
    if not questions.ocean_confirm_release(package_id, version or "?", security).ask():
        typer.secho("Aborted.", fg=typer.colors.YELLOW)
        raise typer.Exit()
    try: updated = ocean.release(ptype, package_id, data, checksum, security=security)
    except OceanError as e:
        typer.secho(f"Release failed: {humanize_error(e.detail)}", fg=typer.colors.RED)
        raise typer.Exit(1)
    typer.secho(f"Released '{package_id}'" + (f" {version}." if version else "."), fg=typer.colors.GREEN, bold=True)
    _review_notice(updated)


def publish(
        security: bool = typer.Option(
            False, "--security",
            help="Mark a new release of an existing package as a security update."
        )
):
    project_root = Path.cwd()
    ocean = Ocean()
    if not ocean.authenticated:
        typer.secho(
            f"Publishing requires login. Run '{CLI_NAME} {HUB_NAME.lower()} login' first.",
            fg=typer.colors.RED
        )
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

    selected, sensitive, links = scan(project_root)
    reserved = [rel for rel in selected if rel in RESERVED_FILES]
    if reserved:
        typer.secho(
            f"{', '.join(reserved)}: the {HUB_NAME} writes these license documents into every download. "
            "Remove or rename them before publishing.",
            fg=typer.colors.RED
        )
        raise typer.Exit(1)
    _report_skipped(sensitive, links)

    existing = _existing(ocean, ptype, package_id)
    if existing is not None:
        typer.secho("Building package archive...", bold=True)
        data = build_archive(project_root, selected)
        _release(ocean, ptype, package_id, existing, data, sha256_hex(data),
                 _detect_version(project_root, ptype), security)
        return
    if security:
        typer.secho("--security only applies to new releases of a published package; ignoring it.",
                    fg=typer.colors.YELLOW)

    typer.secho(f"Publishing {ptype[:-1]} '{package_id}'...", bold=True)

    try: status = ocean.maintainers()
    except OceanError as e:
        typer.secho(
            f"Could not load your maintainer accounts: {humanize_error(e.detail)}",
            fg=typer.colors.RED
        )
        raise typer.Exit(1)

    orga = _choose_maintainer(status)
    price = _choose_price(ptype)

    typer.secho("Building package archive...", bold=True)
    data = build_archive(project_root, selected)
    checksum = sha256_hex(data)

    try: pkg = ocean.publish(ptype, data, checksum, orga=orga, price=price)
    except OceanError as e:
        typer.secho(f"Publish failed: {humanize_error(e.detail)}",
                    fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"Published '{pkg['id']}'.", fg=typer.colors.GREEN, bold=True)
    _review_notice(pkg)

    if pkg.get("license_missing"):
        _select_license(ocean, ptype, pkg["id"])
