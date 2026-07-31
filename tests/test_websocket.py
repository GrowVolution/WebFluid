import asyncio, pytest, uvicorn, websockets


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


async def exchange(fluid, port, message):
    await fluid._lifecycle.run_startup()
    server, task = await serve(fluid, port)

    try:
        async with websockets.connect(f"ws://127.0.0.1:{port}/ws/events") as ws:
            await ws.send(message)
            return await asyncio.wait_for(ws.recv(), timeout=3)
    finally:
        server.should_exit = True
        await task


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
