from fastapi.responses import HTMLResponse, StreamingResponse
import pytest

from webfluid.core.constants import FRAMEWORK_STATIC


@pytest.fixture
def app(make_fluid):
    fluid = make_fluid()

    @fluid.get("/json")
    async def json_route(): return { "ok": True }

    @fluid.get("/page")
    async def page():
        return HTMLResponse(await fluid.render("page.html", greeting="moin"))

    @fluid.get("/stream")
    async def stream():
        async def chunks():
            for i in range(3): yield f"chunk{i}".encode()
        return StreamingResponse(chunks(), media_type="text/plain")

    return fluid


@pytest.mark.asyncio
async def test_json_route_passes_through(app, client):
    async with client(app) as c:
        response = await c.get("/json")

    assert response.status_code == 200
    assert response.json() == { "ok": True }


@pytest.mark.asyncio
async def test_template_rendering(app, client):
    async with client(app) as c:
        response = await c.get("/page")

    assert response.text == "<html><body>moin</body></html>"


async def drive(fluid, path):
    messages = []
    events = [{ "type": "http.request", "body": b"", "more_body": False }]

    async def receive():
        if events: return events.pop(0)
        return { "type": "http.disconnect" }

    async def send(message): messages.append(message)

    await fluid(
        {
            "type": "http", "asgi": { "version": "3.0" }, "http_version": "1.1",
            "method": "GET", "path": path, "raw_path": path.encode(),
            "query_string": b"", "root_path": "", "scheme": "http",
            "headers": [(b"host", b"testserver")],
            "client": ("127.0.0.1", 1234), "server": ("testserver", 80)
        },
        receive, send
    )

    return [m for m in messages if m["type"] == "http.response.body"]


@pytest.mark.asyncio
async def test_streaming_response_is_not_buffered(app):
    app.after_request(lambda response: response)
    await app._lifecycle.run_startup()

    bodies = await drive(app, "/stream")

    assert len(bodies) > 2
    assert b"".join(m.get("body", b"") for m in bodies) == b"chunk0chunk1chunk2"


@pytest.mark.asyncio
async def test_regular_response_is_buffered_for_processors(app):
    app.after_request(lambda response: response)
    await app._lifecycle.run_startup()

    bodies = await drive(app, "/json")

    assert len(bodies) == 1


@pytest.mark.asyncio
async def test_processors_run_in_order(app, client):
    calls = []

    app.before_request(lambda: calls.append("before"))
    app.after_request(lambda response: calls.append("first") or response)
    app.after_request(lambda response: calls.append("second") or response)

    async with client(app) as c:
        await c.get("/json")

    assert calls == ["before", "second", "first"]


@pytest.mark.asyncio
async def test_before_processor_can_short_circuit(app, client):
    app.before_request(lambda: HTMLResponse("stopped", status_code=418))

    async with client(app) as c:
        response = await c.get("/json")

    assert response.status_code == 418
    assert response.text == "stopped"


@pytest.mark.asyncio
async def test_after_processor_can_replace_the_response(app, client):
    app.after_request(lambda response: HTMLResponse("replaced"))

    async with client(app) as c:
        response = await c.get("/json")

    assert response.text == "replaced"
    assert response.headers["content-length"] == str(len("replaced"))


@pytest.mark.asyncio
async def test_static_requests_skip_the_pipeline(app, client):
    calls = []
    app.before_request(lambda: calls.append("hit"))

    async with client(app) as c:
        response = await c.get(f"{FRAMEWORK_STATIC}/js/base.js")

    assert response.status_code == 200
    assert calls == []


@pytest.mark.asyncio
async def test_static_files_are_cacheable(app, client):
    async with client(app) as c:
        response = await c.get(f"{FRAMEWORK_STATIC}/js/base.js")

    assert response.headers["cache-control"] == "public, max-age=31536000"


@pytest.mark.asyncio
async def test_url_path_for_uses_the_index(app, client):
    async with client(app) as c:
        await c.get("/json")

    assert app.url_path_for("json_route") == "/json"
    assert app._routes._count == len(app.routes)


def test_deprecated_app_root_still_resolves(app):
    with pytest.deprecated_call():
        assert app.app_root == app.project_root


@pytest.mark.asyncio
async def test_request_context_is_truthy_without_data(app, client):
    from webfluid.core.context import FluidContext

    seen = {}

    @app.get("/context")
    async def context_route():
        ctx = FluidContext.try_current()
        seen["length"] = len(ctx)
        seen["request"] = ctx.request if ctx else None
        return { "ok": True }

    async with client(app) as c:
        await c.get("/context")

    assert seen["length"] == 0
    assert seen["request"] is not None


def test_url_for_falls_back_to_the_route_table_off_request(app):
    from webfluid.core.processing.context.url_for import url_for

    resolve = url_for(app)

    assert resolve("json_route") == "/json"
    assert resolve("json_route", external=True) == \
        f"{app.config['BASE_URL'].rstrip('/')}/json"


@pytest.mark.asyncio
async def test_url_for_uses_the_request_when_there_is_one(app, client):
    from webfluid.core.processing.context.url_for import url_for

    seen = {}

    @app.get("/urls")
    async def urls():
        resolve = url_for(app)
        seen["path"] = resolve("json_route")
        seen["external"] = resolve("json_route", external=True)
        return { "ok": True }

    async with client(app) as c:
        await c.get("/urls")

    assert seen["path"] == "/json"
    assert seen["external"] == "http://testserver/json"
