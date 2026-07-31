from pathlib import Path
import asyncio, os, subprocess, sys, tempfile, time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("SECRET_KEY", "benchmark")

from webfluid.core.identity import FRAMEWORK_ID, FRAMEWORK_PACKAGE

BUDGETS = {
    "import Fluid": 900,
    "import cli": 400,
    "render": 300,
    "request": 150
}


async def call(fluid, path):
    events = [{ "type": "http.request", "body": b"", "more_body": False }]

    async def receive():
        return events.pop(0) if events else { "type": "http.disconnect" }

    async def send(message): pass

    await fluid(
        {
            "type": "http", "asgi": { "version": "3.0" }, "http_version": "1.1",
            "method": "GET", "path": path, "raw_path": path.encode(),
            "query_string": b"", "root_path": "", "scheme": "http",
            "headers": [(b"host", b"benchmark")],
            "client": ("127.0.0.1", 1), "server": ("benchmark", 80)
        },
        receive, send
    )


def measure_import(statement):
    result = subprocess.run(
        [sys.executable, "-X", "importtime", "-c", statement],
        capture_output=True, text=True
    )
    total = 0
    for line in result.stderr.splitlines():
        parts = line.split("|")
        if len(parts) == 3 and FRAMEWORK_PACKAGE in parts[2]:
            total = max(total, int(parts[1].strip()))
    return total / 1000


def project():
    root = Path(tempfile.mkdtemp())
    templates = root / FRAMEWORK_ID / "templates"
    templates.mkdir(parents=True)

    (templates / "base.html").write_text("<html><body>{% block c %}{% endblock %}</body></html>")
    (templates / "part.html").write_text("<p>{{ x }}</p>")
    (templates / "page.html").write_text(
        "{% extends 'base.html' %}{% block c %}"
        "{% for i in range(20) %}{% include 'part.html' %}{% endfor %}"
        "{% endblock %}"
    )
    return root


async def measure_runtime(root, rounds=2000):
    import webfluid.core.fluid.main as main

    main.get_root_path = lambda _: str(root)
    from webfluid import Fluid

    fluid = Fluid("benchmark")

    @fluid.get("/ping")
    async def ping(): return { "ok": True }

    await fluid._lifecycle.run_startup()

    for _ in range(200): await fluid.render("page.html", x=1)
    start = time.perf_counter()
    for _ in range(rounds): await fluid.render("page.html", x=1)
    render = (time.perf_counter() - start) / rounds * 1e6

    for _ in range(200): await call(fluid, "/ping")
    start = time.perf_counter()
    for _ in range(rounds): await call(fluid, "/ping")
    request = (time.perf_counter() - start) / rounds * 1e6

    return render, request


def main():
    results = {
        "import Fluid": measure_import("from webfluid import Fluid"),
        "import cli": measure_import("from webfluid.cli import wf")
    }

    render, request = asyncio.run(measure_runtime(project()))
    results["render"] = render
    results["request"] = request

    units = { "import Fluid": "ms", "import cli": "ms" }
    failed = False

    for name, value in results.items():
        budget = BUDGETS[name]
        unit = units.get(name, "us")
        status = "ok " if value <= budget else "OVER"
        if value > budget: failed = True
        print(f"{status} {name:16s} {value:8.1f} {unit:2s} (budget {budget} {unit})")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
