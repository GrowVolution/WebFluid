import asyncio, json, pytest, uvicorn, websockets


@pytest.fixture
def events_app(make_fluid):
    from webfluid.extensions.events.main import EventManager

    fluid = make_fluid()
    manager = EventManager()
    manager.expand_fluid(fluid)

    return fluid, manager


async def serve(app, port):
    server = uvicorn.Server(uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="critical"
    ))
    task = asyncio.create_task(server.serve())

    while not server.started: await asyncio.sleep(0.02)
    return server, task


async def exchange(fluid, port, message, extra=None, headers=None):
    await fluid._lifecycle.run_startup()
    server, task = await serve(fluid, port)

    try:
        async with websockets.connect(
                f"ws://127.0.0.1:{port}/ws/events",
                additional_headers=headers
        ) as ws:
            await ws.send(message)
            reply = await asyncio.wait_for(ws.recv(), timeout=3)
            if extra is None: return reply

            await ws.send(extra)
            return reply, await asyncio.wait_for(ws.recv(), timeout=3)
    finally:
        server.should_exit = True
        await task


def _request(msg_id, query, data=None):
    return json.dumps({
        "id": msg_id, "type": "request",
        "data": { "query": query, "data": data }
    })


@pytest.mark.asyncio
async def test_events_socket_stays_open_under_uvicorn(events_app):
    fluid, manager = events_app
    manager.create_signal("ping")

    reply = await exchange(
        fluid, 8471, '{"id": 1, "type": "subscribe", "data": "ping"}'
    )

    assert '"data"' in reply and "true" in reply.lower()


@pytest.mark.asyncio
async def test_unknown_request_is_answered(events_app):
    fluid, _ = events_app

    reply = await exchange(
        fluid, 8472, '{"id": 2, "type": "nonsense", "data": null}'
    )

    assert "Unknown request" in reply


@pytest.mark.asyncio
async def test_query_sees_the_connection_as_request(events_app):
    from webfluid.core.context import FluidContext

    fluid, manager = events_app

    @manager.query("connection", internal=False)
    async def describe(_):
        request = FluidContext.current().request
        return {
            "type": request.scope["type"],
            "lang": request.headers.get("Accept-Language")
        }

    reply = await exchange(
        fluid, 8473, _request(3, "connection"),
        headers={"Accept-Language": "de-DE,de;q=0.9"}
    )

    assert json.loads(reply)["data"] == {
        "type": "websocket", "lang": "de-DE,de;q=0.9"
    }


@pytest.mark.asyncio
async def test_failing_query_keeps_the_socket_open(events_app):
    fluid, manager = events_app

    @manager.query("boom", internal=False)
    async def boom(_): raise RuntimeError("nope")

    @manager.query("fine", internal=False)
    async def fine(_): return "ok"

    failed, recovered = await exchange(
        fluid, 8474, _request(4, "boom"), _request(5, "fine")
    )

    assert json.loads(failed)["error"] == "Query 'boom' failed."
    assert json.loads(recovered)["data"] == "ok"


@pytest.mark.asyncio
async def test_internal_query_is_not_reachable(events_app):
    fluid, manager = events_app

    @manager.query("secret")
    async def secret(_): return "leaked"

    reply = await exchange(fluid, 8475, _request(6, "secret"))

    assert json.loads(reply)["error"] == "Query 'secret' is not public."


@pytest.mark.asyncio
@pytest.mark.parametrize("port,message,expected", [
    (8476, '5', "message must be an object"),
    (8477, '["subscribe"]', "message must be an object"),
    (8478, '"ping"', "message must be an object"),
    (8479, 'null', "message must be an object"),
    (8480, '{"id": 1, "type": "subscribe"}', "missing 'data' in message"),
    (8481, 'not json at all', "invalid json"),
])
async def test_a_malformed_message_is_answered(events_app, port, message, expected):
    fluid, _ = events_app

    reply = await exchange(fluid, port, message)

    assert json.loads(reply)["error"] == expected


@pytest.mark.asyncio
async def test_a_malformed_message_keeps_the_socket_open(events_app):
    fluid, manager = events_app
    manager.create_signal("ping")

    broken, recovered = await exchange(
        fluid, 8482, '5', '{"id": 7, "type": "subscribe", "data": "ping"}'
    )

    assert json.loads(broken)["error"] == "message must be an object"
    assert json.loads(recovered)["data"] is True


@pytest.mark.asyncio
async def test_a_binary_frame_is_answered(events_app):
    fluid, _ = events_app

    await fluid._lifecycle.run_startup()
    server, task = await serve(fluid, 8483)

    try:
        async with websockets.connect("ws://127.0.0.1:8483/ws/events") as ws:
            await ws.send(b"\x00\x01\x02")
            reply = await asyncio.wait_for(ws.recv(), timeout=3)
    finally:
        server.should_exit = True
        await task

    assert json.loads(reply)["error"] == "only text frames are supported"


def test_leaving_drops_the_subscriptions(events_app):
    from webfluid.extensions.events.socket.main import SocketManager

    fluid, manager = events_app
    sockets = SocketManager(fluid, manager._events, manager._queries)

    first = sockets.join(object())
    second = sockets.join(object())
    for sid in (first, second): sockets.subscribe("ping", sid)

    sockets.leave(first)
    assert sockets.has_subscriptions("ping", second)
    assert not sockets.has_subscriptions("ping", first)

    sockets.leave(second)
    assert sockets._subscriptions == {}
    assert sockets._websockets == {}


def test_unsubscribing_without_a_subscription_is_an_error(events_app):
    from webfluid.extensions.events.socket.handler.unsubscribe import unsubscribe
    from webfluid.extensions.events.socket.main import SocketManager

    fluid, manager = events_app
    manager.create_signal("ping")
    sockets = SocketManager(fluid, manager._events, manager._queries)

    mine, theirs = sockets.join(object()), sockets.join(object())
    sockets.subscribe("ping", theirs)

    response = unsubscribe(
        sockets, manager._events, mine,
        { "id": 1, "data": "ping" }, { "id": 1 }
    )

    assert "error" in response
    assert sockets.has_subscriptions("ping", theirs)
