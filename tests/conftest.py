from pathlib import Path
import os, sys, pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

os.environ.setdefault("SECRET_KEY", "test-secret-key")

_STATUSES = (400, 401, 403, 404, 405, 429, 500, 502, 503)


def build_project(root):
    templates = root / "fluid" / "templates"
    (templates / "errors" / "debug").mkdir(parents=True, exist_ok=True)
    (root / "fluid" / "static" / "css").mkdir(parents=True, exist_ok=True)

    (templates / "page.html").write_text(
        "<html><body>{{ greeting }}</body></html>", encoding="utf-8"
    )
    for status in _STATUSES:
        (templates / "errors" / f"{status}.html").write_text(
            f"<html><body>error {status}</body></html>", encoding="utf-8"
        )

    return root


@pytest.fixture
def project(tmp_path):
    return build_project(tmp_path)


@pytest.fixture
def make_fluid(project, monkeypatch):
    def factory(name="tests.app"):
        monkeypatch.setattr(
            "webfluid.core.fluid.main.get_root_path", lambda _: str(project)
        )

        from webfluid import Fluid
        return Fluid(name)

    return factory


@pytest.fixture
def client():
    from contextlib import asynccontextmanager
    import httpx

    @asynccontextmanager
    async def factory(fluid):
        await fluid._lifecycle.run_startup()
        transport = httpx.ASGITransport(app=fluid)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
        ) as c: yield c

    return factory
