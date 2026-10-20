import ast, pytest

from webfluid.cli.create import templates
from webfluid.core.fluid.main import _project_root
from webfluid.core.identity import (
    FRAMEWORK_ID, FRAMEWORK_PACKAGE, FRAMEWORK_ROOT
)

_ENV = FRAMEWORK_ROOT / "extensions/migrate/templates"

_INDEX = (
    f"\n    from {FRAMEWORK_ID}.app import app_router"
    f"\n    app.include_router(app_router)\n"
)


@pytest.mark.parametrize("index", ["", _INDEX])
def test_the_generated_factory_carries_no_placeholder(index):
    source = templates.app_init_py.format(index=index)

    assert "{index}" not in source

    tree = ast.parse(source)
    factory = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
    )
    assert factory.name == f"prepare_{FRAMEWORK_ID}"


def test_the_generated_factory_includes_the_app_router():
    source = templates.app_init_py.format(index=_INDEX)

    assert f"from {FRAMEWORK_ID}.app import app_router" in source
    assert f"from {FRAMEWORK_ID}.api import api_router" in source


def test_the_generated_entrypoint_calls_the_factory():
    ast.parse(templates.main_py)

    assert f"from {FRAMEWORK_ID} import prepare_{FRAMEWORK_ID}" \
           in templates.main_py
    assert "{" not in templates.main_py


@pytest.mark.parametrize("template", ["single_db", "multi_db"])
def test_the_migration_environment_renders_from_the_seam(template):
    source = (_ENV / template / "migrations/env.py.mako") \
        .read_text(encoding="utf-8") \
        .replace("{package}", FRAMEWORK_PACKAGE) \
        .replace("{id}", FRAMEWORK_ID)

    assert "{id}" not in source and "{package}" not in source
    assert f"prepare_{FRAMEWORK_ID}" in source
    assert f"from {FRAMEWORK_PACKAGE}.core.context" in source
    ast.parse(source)


def test_the_app_package_resolves_to_the_project_root(tmp_path, monkeypatch):
    app_dir = tmp_path / FRAMEWORK_ID
    app_dir.mkdir()
    (app_dir / "__init__.py").touch()
    monkeypatch.setattr(
        "webfluid.core.fluid.main.get_root_path", lambda _: str(app_dir)
    )

    assert _project_root(FRAMEWORK_ID) == tmp_path


def test_a_plain_module_keeps_its_own_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "webfluid.core.fluid.main.get_root_path", lambda _: str(tmp_path)
    )

    assert _project_root("__main__") == tmp_path


def test_a_project_root_named_after_the_framework_is_kept(tmp_path, monkeypatch):
    root = tmp_path / FRAMEWORK_ID
    root.mkdir()
    monkeypatch.setattr(
        "webfluid.core.fluid.main.get_root_path", lambda _: str(root)
    )

    assert _project_root("__main__") == root


def test_a_project_without_a_frontend_is_complete(tmp_path, monkeypatch):
    from webfluid.cli.create.project import project

    monkeypatch.chdir(tmp_path)
    project("site", False, True, False)

    root = tmp_path / "site"
    app_dir = root / FRAMEWORK_ID

    assert (root / "main.py").exists()
    assert (app_dir / "__init__.py").exists()
    assert (app_dir / "config.py").exists()

    for path in ("main.py", f"{FRAMEWORK_ID}/__init__.py", f"{FRAMEWORK_ID}/config.py"):
        ast.parse((root / path).read_text(encoding="utf-8"))

    config = (app_dir / "config.py").read_text(encoding="utf-8")
    assert "'type': 'none'" in config
    assert '"title": "site"' in config
