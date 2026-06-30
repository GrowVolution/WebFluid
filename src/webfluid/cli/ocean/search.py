import typer

from webfluid.utils.ocean import Ocean, humanize_error
from webfluid.exceptions import OceanError
from webfluid.cli.ocean.output import render_table, truncate, package_state


def _types(additives, extensions, bundles):
    if additives or extensions or bundles:
        selected = []
        if additives: selected.append("additives")
        if extensions: selected.append("extensions")
        if bundles: selected.append("bundles")
        return selected

    return ["additives", "extensions", "bundles"]


def _license(oss_only, paid_only):
    if oss_only and paid_only:
        typer.secho(
            "Using --oss-only and --paid-only together is equivalent "
            "to using neither.",
            fg=typer.colors.YELLOW
        )
        return ""
    if oss_only: return "open"
    if paid_only: return "paid"
    return ""


def _packages_table(items):
    typer.secho("\nAdditives & Extensions", bold=True)
    rows = [[
        item["type"][:-1],
        item["id"],
        item.get("name") or "",
        item.get("description") or "",
        item.get("version") or "—",
        item.get("date") or "—",
        package_state(item)
    ] for item in items]
    typer.echo(render_table(
        ["type", "id", "name", "description", "version", "released", "price"],
        rows,
        max_widths=[10, 24, 24, 40, 12, 14, 10]
    ))


def _bundles_table(items):
    typer.secho("\nBundles", bold=True)
    rows = []
    for item in items:
        contents = ", ".join(
            f"{entry['id']} ({entry['type']})"
            for entry in item.get("items", [])
        )
        rows.append([
            item["id"],
            truncate(contents, 60),
            package_state(item)
        ])
    typer.echo(render_table(
        ["bundle", "contents", "price"],
        rows,
        max_widths=[24, 60, 10]
    ))


def search(
        query: str = typer.Argument(
            "", help="Search query for package ids."
        ),
        additives: bool = typer.Option(
            False, "--additives", "-a",
            help="Restrict results to additives."
        ),
        extensions: bool = typer.Option(
            False, "--extensions", "-e",
            help="Restrict results to extensions."
        ),
        bundles: bool = typer.Option(
            False, "--bundles", "-b",
            help="Restrict results to bundles."
        ),
        oss_only: bool = typer.Option(
            False, "--oss-only",
            help="Only open-source packages."
        ),
        paid_only: bool = typer.Option(
            False, "--paid-only",
            help="Only paid packages."
        )
):
    types = _types(additives, extensions, bundles)
    license = _license(oss_only, paid_only)

    try: items = Ocean().search(query, types, license)
    except OceanError as e:
        typer.secho(f"Search failed: {humanize_error(e.detail)}",
                    fg=typer.colors.RED)
        raise typer.Exit(1)

    packages = [i for i in items if i["type"] in ("additives", "extensions")]
    bundle_items = [i for i in items if i["type"] == "bundles"]

    if not packages and not bundle_items:
        typer.secho("No packages found.", fg=typer.colors.YELLOW)
        return

    if packages: _packages_table(packages)
    if bundle_items: _bundles_table(bundle_items)
