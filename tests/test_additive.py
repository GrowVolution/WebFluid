from pathlib import Path
import json, os, shutil, sys, tempfile, pytest

from webfluid.exceptions import AdditiveException


def write_additive(root, aid, manifest=None, kind="default"):
    package = root / aid
    (package / "templates").mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text("", encoding="utf-8")

    data = {
        "id": aid,
        "version": "1.0.0",
        "type": kind,
        "frontend": { "type": "none" }
    }
    if manifest: data.update(manifest)

    (package / "manifest.json").write_text(json.dumps(data), encoding="utf-8")
    return package


@pytest.fixture
def additives():
    root = Path(tempfile.mkdtemp())
    package = root / "additives"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")

    sys.path.insert(0, str(root))
    yield package

    sys.path.remove(str(root))
    for name in [m for m in sys.modules if m.startswith("additives")]:
        del sys.modules[name]
    shutil.rmtree(root, ignore_errors=True)


def build(additives, aid, **kwargs):
    write_additive(additives, aid, **kwargs)

    from webfluid.core.additive import Additive
    return Additive(f"additives.{aid}")


def test_request_hooks_are_registrable(additives):
    additive = build(additives, "demo")

    @additive.before_request
    def before(): return None

    @additive.after_request
    def after(response): return response

    assert before in list(additive._request_lifecycle.before)
    assert after in list(additive._request_lifecycle.after)


def test_enable_hooks_check_their_arity(additives):
    additive = build(additives, "demo")

    additive.before_enable(lambda fluid: None)
    additive.after_enable(lambda: None)

    with pytest.raises(TypeError): additive.before_enable(lambda: None)
    with pytest.raises(TypeError): additive.after_enable(lambda fluid: None)


def test_version_is_parsed_once(additives):
    additive = build(additives, "demo", manifest={ "version": "2.1.0b3" })

    assert str(additive.version) == "2.1.0b3"
    assert additive.version.stage == "b"
    assert additive.version.build == 3


def test_feature_additive_gets_prefixed_routers(additives):
    additive = build(additives, "demo")

    assert additive.api.prefix == "/api"
    assert additive.ws.prefix == "/ws"
    assert additive.frontend is not None
    assert additive._jinja.loader is not None


def test_base_additive_has_no_frontend_and_no_prefixes(additives):
    additive = build(additives, "core_base", kind="base")

    assert additive.api.prefix == ""
    assert additive.ws.prefix == ""
    assert additive.frontend is None
    assert additive._jinja.loader is None


def test_base_additive_refuses_to_be_enabled(additives):
    additive = build(additives, "core_base", kind="base")

    with pytest.raises(AdditiveException): additive.check_enable()


def test_requirement_check_does_not_consume_the_manifest(additives):
    additive = build(additives, "demo", manifest={
        "requires": { "wf": "*", "additives": { "missing": "*" } }
    })

    for _ in range(2):
        with pytest.raises(AdditiveException):
            additive.manifest.check_requirements(additives)

    assert additive.manifest["requires"]["additives"] == { "missing": "*" }


def test_requirement_check_accepts_the_list_form(additives):
    write_additive(additives, "dependency", manifest={ "version": "1.2.0" })
    additive = build(additives, "demo", manifest={
        "requires": { "wf": "*", "additives": ["dependency@>=1.0"] }
    })

    os.environ["dependency"] = "1"
    try: additive.manifest.check_requirements(additives)
    finally: os.environ.pop("dependency", None)
