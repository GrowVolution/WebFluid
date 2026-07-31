from pathlib import Path
import ast, re, shutil, subprocess, keyword, typer, questionary

ROOT = Path(__file__).resolve().parents[1]

style = questionary.Style.from_dict({
    "qmark": "fg:#ff9d00 bold",
    "question": "bold",
    "pointer": "fg:#ff9d00 bold",
    "highlighted": "bold",
    "selected": "fg:#00aa00",
    "answer": "fg:#00aa00 bold",
    "separator": "fg:#888888",
    "text": ""
})

qmark = ">"

SEAM = (
    "FRAMEWORK_ID", "FRAMEWORK_NAME", "FRAMEWORK_ABBR",
    "FRAMEWORK_SITE", "FRAMEWORK_DOCS",
    "HUB_NAME", "HUB_API_URL", "HUB_AUTH_URL"
)

SKIP = { "__pycache__", ".git", ".idea", ".vscode", ".venv", "node_modules", "dist", "build" }
SUFFIXES = { ".py", ".pyi", ".html", ".css", ".js", ".json", ".toml", ".cfg", ".md", ".txt" }
NAMED = { "Dockerfile" }

VOCABULARY = (
    "Fluid", "FluidContext", "FluidExtension", "FluidVersion",
    "Additive", "Ocean", "OceanError"
)


def text(message, **kwargs):
    return questionary.text(message, qmark=qmark, style=style, **kwargs)


def confirm(message, **kwargs):
    return questionary.confirm(message, qmark=qmark, style=style, **kwargs)


def identifier(value):
    value = value.strip()
    if not value: return "Cannot be empty."
    if not value.isidentifier(): return "Must be a valid Python identifier."
    if keyword.iskeyword(value): return "Cannot be a Python keyword."
    if value != value.lower(): return "Must be lowercase."
    return True


def abbreviation(value):
    value = value.strip()
    if not re.fullmatch(r"[a-z][a-z0-9]{0,7}", value):
        return "Two to eight lowercase letters or digits, starting with a letter."
    return True


def word(value):
    value = value.strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", value):
        return "Letters and digits only, starting with a letter."
    return True


def filled(value):
    return True if value.strip() else "Cannot be empty."


def url(value):
    value = value.strip()
    if not value.startswith(("http://", "https://")):
        return "Must start with http:// or https://."
    return True


def locate():
    src = ROOT / "src"
    if src.is_dir():
        for package in sorted(src.iterdir()):
            if (package / "core" / "identity.py").exists():
                return package, package / "core" / "identity.py"

    typer.secho("No identity seam found under src/*/core/identity.py.",
                fg=typer.colors.RED)
    raise typer.Exit(1)


def read_seam(seam):
    values = {}
    for node in ast.parse(seam.read_text(encoding="utf-8")).body:
        if not isinstance(node, ast.Assign): continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in SEAM: continue
        if isinstance(node.value, ast.Constant):
            values[target.id] = node.value.value

    missing = [key for key in SEAM if key not in values]
    if missing:
        typer.secho(f"Seam has no literal value for: {', '.join(missing)}",
                    fg=typer.colors.RED)
        raise typer.Exit(1)

    return values


def ask(old, package):
    typer.secho("\nAnswer with the values your fork should carry. "
                "Empty keeps the current one.\n", bold=True)

    def answer(message, default, validate):
        value = text(f"{message}:", default=default, validate=validate).ask()
        if value is None: raise typer.Abort()
        return value.strip()

    new = {
        "FRAMEWORK_ID": answer(
            "Framework id (asset folder, template prefix, project app folder)",
            old["FRAMEWORK_ID"], identifier
        ),
        "FRAMEWORK_NAME": answer(
            "Display name (CLI, logs, page titles)",
            old["FRAMEWORK_NAME"], filled
        ),
        "FRAMEWORK_ABBR": answer(
            "Abbreviation (CLI command, env prefix, jinja globals, css classes)",
            old["FRAMEWORK_ABBR"], abbreviation
        ),
        "FRAMEWORK_SITE": answer("Website", old["FRAMEWORK_SITE"], url),
        "FRAMEWORK_DOCS": answer("Documentation", old["FRAMEWORK_DOCS"], url),
        "HUB_NAME": answer(
            "Package hub name (its cli sub command too)",
            old["HUB_NAME"], word
        ),
        "HUB_API_URL": answer("Hub api endpoint", old["HUB_API_URL"], url),
        "HUB_AUTH_URL": answer("Hub auth endpoint", old["HUB_AUTH_URL"], url)
    }

    new_package = answer(
        "Distribution and import package name", package.name, identifier
    )

    if new_package == new["FRAMEWORK_ID"]:
        typer.secho("\nPackage name and framework id must differ: the id names "
                    "a folder inside the package.", fg=typer.colors.RED)
        raise typer.Exit(1)

    return new, new_package


def rules(old, new, package, new_package):
    old_id, new_id = old["FRAMEWORK_ID"], new["FRAMEWORK_ID"]
    old_abbr, new_abbr = old["FRAMEWORK_ABBR"], new["FRAMEWORK_ABBR"]

    return (
        (rf"\b{re.escape(package.name)}\b", new_package),
        (rf"\b{re.escape(new_package)}\.{re.escape(old_id)}\b", f"{new_package}.{new_id}"),
        (rf"\b{re.escape(old_id)}_base\.html\b", f"{new_id}_base.html"),
        (rf"\b{re.escape(old_abbr)}_", f"{new_abbr}_"),
        (rf"\b{re.escape(old_abbr)}-", f"{new_abbr}-"),
        (rf"\b{re.escape(old_abbr)}\b", new_abbr),
        (rf"\b{re.escape(old['FRAMEWORK_NAME'])}\b", new["FRAMEWORK_NAME"])
    )


def targets(old, new, package):
    old_id, new_id = old["FRAMEWORK_ID"], new["FRAMEWORK_ID"]
    stub = ROOT / "stubs" / "src" / f"{package.name}-stubs" / "__init__.pyi"

    return (
        (package / "__init__.py", f'"{old_id}"', f'"{new_id}"'),
        (stub, f'"{old_id}"', f'"{new_id}"'),
        (stub, f"{old_id} as {old_id}", f"{new_id} as {new_id}"),
        (ROOT / "pyproject.toml", f'"{old_id}/', f'"{new_id}/')
    )


def renames(old, new, package, new_package):
    old_id, new_id = old["FRAMEWORK_ID"], new["FRAMEWORK_ID"]
    old_abbr, new_abbr = old["FRAMEWORK_ABBR"], new["FRAMEWORK_ABBR"]
    stubs = ROOT / "stubs" / "src" / f"{package.name}-stubs"

    pairs = [(
        package / old_id / "templates" / f"{old_id}_base.html",
        package / old_id / "templates" / f"{new_id}_base.html"
    )]

    for root, suffix in ((package, ".py"), (stubs, ".pyi")):
        pairs += [
            (root / old_id, root / new_id),
            (root / "cli" / f"{old_abbr}{suffix}", root / "cli" / f"{new_abbr}{suffix}"),
            (root / "surface" / f"{old_abbr}_node{suffix}",
             root / "surface" / f"{new_abbr}_node{suffix}"),
            (root / "surface" / f"{old_abbr}_tailwind{suffix}",
             root / "surface" / f"{new_abbr}_tailwind{suffix}")
        ]

    pairs += [
        (stubs, stubs.parent / f"{new_package}-stubs"),
        (package, package.parent / new_package)
    ]

    return [(src, dst) for src, dst in pairs if src != dst and src.exists()]


def sources():
    found = []
    for path in ROOT.rglob("*"):
        if not path.is_file(): continue
        if SKIP & set(path.relative_to(ROOT).parts): continue
        if path.suffix in SUFFIXES or path.name in NAMED: found.append(path)
    return found


def rewrite(files, patterns, seam, write):
    touched = []
    for file in files:
        if file == seam: continue
        try: source = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError): continue

        updated = source
        for pattern, value in patterns:
            updated = re.sub(pattern, lambda _, v=value: v, updated)

        if updated == source: continue
        touched.append(file)
        if write: file.write_text(updated, encoding="utf-8")

    return touched


def retarget(pairs, write):
    touched = []
    for file, old, new in pairs:
        if not file.exists(): continue
        source = file.read_text(encoding="utf-8")
        if old not in source: continue

        if file not in touched: touched.append(file)
        if write: file.write_text(source.replace(old, new), encoding="utf-8")

    return touched


def reseat(seam, values, write):
    source = seam.read_text(encoding="utf-8")
    for key, value in values.items():
        source = re.sub(
            rf'^{key} = ".*"$',
            lambda _, k=key, v=value: f'{k} = "{v}"',
            source, count=1, flags=re.MULTILINE
        )
    if write: seam.write_text(source, encoding="utf-8")


def sweep():
    for cache in ROOT.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    for info in (ROOT / "src").glob("*.egg-info"):
        shutil.rmtree(info, ignore_errors=True)


def leftovers(old, package):
    tokens = (package.name, old["FRAMEWORK_NAME"], old["FRAMEWORK_ABBR"])
    found = []

    for file in sources():
        try: source = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError): continue

        for number, line in enumerate(source.splitlines(), 1):
            for token in tokens:
                if re.search(rf"\b{re.escape(token)}\b", line):
                    found.append((file.relative_to(ROOT), number, token))
                    break

    return found


def dirty():
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT, capture_output=True, text=True
        )
    except OSError: return False
    return result.returncode == 0 and bool(result.stdout.strip())


def preview(old, new, package, new_package, files, moves):
    typer.secho("\nThe fork will carry:\n", bold=True)

    changes = [("package", package.name, new_package)]
    changes += [(key, old[key], new[key]) for key in SEAM]

    width = max(len(key) for key, _, _ in changes)
    for key, was, becomes in changes:
        arrow = typer.style("->", fg=typer.colors.BRIGHT_BLACK)
        if was == becomes:
            typer.echo(f"  {key.ljust(width)}  {typer.style(was, dim=True)}")
        else:
            typer.echo(f"  {key.ljust(width)}  {was} {arrow} "
                       f"{typer.style(becomes, fg=typer.colors.GREEN, bold=True)}")

    typer.secho(f"\n{len(files)} file(s) rewritten, {len(moves)} path(s) renamed:\n",
                bold=True)
    for src, dst in moves:
        typer.echo(f"  {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")


app = typer.Typer(name="rebrand", add_completion=False)


@app.command()
def rebrand(
        dry_run: bool = typer.Option(
            False,
            "--dry-run", "-n",
            help="Show what would change without touching anything."
        ),
        force: bool = typer.Option(
            False,
            "--force", "-f",
            help="Rebrand even though the working tree has uncommitted changes."
        )
):
    """Make this framework your own: rewrite every seam value, the package
    name and the packaging metadata in one pass."""

    package, seam = locate()
    old = read_seam(seam)

    typer.secho(f"Found '{old['FRAMEWORK_NAME']}' in src/{package.name}.", bold=True)

    if not dry_run and dirty() and not force:
        typer.secho(
            "\nThe working tree has uncommitted changes. A rebrand touches most "
            "of the repository. Commit or stash first, or pass --force.",
            fg=typer.colors.RED
        )
        raise typer.Exit(1)

    new, new_package = ask(old, package)

    if new == old and new_package == package.name:
        typer.secho("\nNothing to change.", fg=typer.colors.YELLOW)
        raise typer.Exit()

    patterns = rules(old, new, package, new_package)
    pairs = targets(old, new, package)
    moves = renames(old, new, package, new_package)

    files = rewrite(sources(), patterns, seam, False)
    files += [file for file in retarget(pairs, False) if file not in files]

    preview(old, new, package, new_package, files, moves)

    if dry_run:
        typer.secho("\nDry run: nothing was written.", fg=typer.colors.YELLOW)
        raise typer.Exit()

    if not confirm("\nApply this to the working tree?", default=False).ask():
        typer.secho("Aborting...", fg=typer.colors.YELLOW)
        raise typer.Exit()

    typer.secho("\nRewriting sources...", bold=True)
    rewrite(sources(), patterns, seam, True)
    retarget(pairs, True)

    typer.secho("Reseating the identity seam...", bold=True)
    reseat(seam, new, True)

    typer.secho("Renaming paths...", bold=True)
    for src, dst in moves:
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)

    sweep()

    typer.secho(f"\nRebranded to {new['FRAMEWORK_NAME']}.",
                bold=True, fg=typer.colors.GREEN)

    remaining = leftovers(old, package)
    if remaining:
        typer.secho(f"\n{len(remaining)} leftover mention(s) of the old brand:",
                    fg=typer.colors.YELLOW, bold=True)
        for file, number, token in remaining[:20]:
            typer.echo(f"  {file}:{number}  {token}")
        if len(remaining) > 20:
            typer.echo(f"  ... and {len(remaining) - 20} more")

    typer.secho("\nLeft untouched on purpose:", bold=True)
    typer.echo(f"  Class and module vocabulary: {', '.join(VOCABULARY)} and the "
               f"modules named after them. Rename those with an IDE refactor.")
    typer.echo("  Version numbers, authors and the license in pyproject.toml.")
    typer.echo(f"  Logos and images in src/{new_package}/{new['FRAMEWORK_ID']}/static/img.")

    typer.secho("\nNext:", bold=True)
    typer.echo(f"  pip install -e \".[test]\"  &&  python -m pytest -q")
    typer.echo(f"  python scripts/check_stubs.py")


if __name__ == "__main__":
    app()
