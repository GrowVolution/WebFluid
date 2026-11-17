from types import SimpleNamespace
import asyncio, pytest

from webfluid.core.lifecycle import (
    AdditiveLifecycle, FluidLifecycle, Phase, RequestLifecycle
)


class Recorder:
    def __init__(self): self.calls = []
    async def run_startup(self): self.calls.append("startup")
    async def run_shutdown(self): self.calls.append("shutdown")


def test_phase_keeps_registration_order():
    phase = Phase("Hooks")
    calls = []

    for i in range(3): phase.add(lambda i=i: calls.append(i))
    for hook in phase: hook()

    assert calls == [0, 1, 2]


def test_reversed_phase_runs_backwards():
    phase = Phase("Hooks", reverse=True)
    calls = []

    for i in range(3): phase.add(lambda i=i: calls.append(i))
    for hook in phase: hook()

    assert calls == [2, 1, 0]


def test_phase_rejects_wrong_arity():
    phase = Phase("Hooks")
    with pytest.raises(TypeError): phase.add(lambda a: None)

    phase = Phase("Processors", arity=1, argument="response")
    with pytest.raises(TypeError): phase.add(lambda: None)
    phase.add(lambda response: response)


def test_phase_closes_after_seal():
    phase = Phase("Hooks", closed_after="the server was started")
    phase.add(lambda: None)
    phase.seal()

    with pytest.raises(RuntimeError): phase.add(lambda: None)


def test_phase_without_closed_after_stays_open():
    phase = Phase("Processors")
    phase.seal()
    phase.add(lambda: None)


@pytest.mark.parametrize("lifecycle, names", [
    (FluidLifecycle, ("startup", "shutdown")),
    (AdditiveLifecycle, ("before_enable", "after_enable")),
    (RequestLifecycle, ("before", "after"))
])
def test_every_lifecycle_registers_through_add(lifecycle, names):
    instance = lifecycle()
    for name in names:
        assert callable(getattr(instance, name).add)


@pytest.mark.asyncio
async def test_before_processor_short_circuits():
    lifecycle = RequestLifecycle()
    lifecycle.before.add(lambda: None)
    lifecycle.before.add(lambda: "response")
    lifecycle.before.add(lambda: "never")

    assert await lifecycle.process_before() == "response"


@pytest.mark.asyncio
async def test_after_processors_chain_in_reverse():
    lifecycle = RequestLifecycle()
    lifecycle.after.add(lambda response: response + "-first")
    lifecycle.after.add(lambda response: response + "-second")

    assert await lifecycle.process_after("r") == "r-second-first"


@pytest.mark.asyncio
async def test_a_failing_server_shuts_down_instead_of_hanging():
    from webfluid.core.fluid.server import Server

    lifecycle = Recorder()
    server = Server(SimpleNamespace(startup_hook=lambda fn: fn), lifecycle)

    async def crash(): raise RuntimeError("address already in use")
    server._run_server = crash

    with pytest.raises(RuntimeError):
        await asyncio.wait_for(server._start(), timeout=5)

    assert lifecycle.calls == ["startup", "shutdown"]


@pytest.mark.asyncio
async def test_a_signalled_server_runs_the_shutdown_phase():
    from webfluid.core.fluid.server import Server

    lifecycle = Recorder()
    server = Server(SimpleNamespace(startup_hook=lambda fn: fn), lifecycle)

    async def serve():
        server._server = SimpleNamespace(should_exit=False)
        server._server.should_exit = True

    server._run_server = serve
    await asyncio.wait_for(server._start(), timeout=5)

    assert lifecycle.calls == ["startup", "shutdown"]


def test_the_server_absorbs_the_signals_uvicorn_re_raises():
    import signal
    from webfluid.core.fluid.server import Server, _SIGNALS

    server = Server(SimpleNamespace(startup_hook=lambda fn: fn), Recorder())
    original = {sig: signal.getsignal(sig) for sig in _SIGNALS}

    try:
        server._absorb_signals()
        for sig in _SIGNALS:
            handler = signal.getsignal(sig)
            assert handler not in (
                signal.SIG_DFL, signal.SIG_IGN, signal.default_int_handler
            )
            assert handler(sig, None) is None
    finally:
        for sig, handler in original.items(): signal.signal(sig, handler)


@pytest.mark.asyncio
async def test_a_failing_startup_phase_still_shuts_down():
    from webfluid.core.fluid.server import Server

    lifecycle = Recorder()
    server = Server(SimpleNamespace(startup_hook=lambda fn: fn), lifecycle)

    async def crash(): raise RuntimeError("startup phase died")
    lifecycle.run_startup = crash
    server._run_server = lambda: pytest.fail("server must not start")

    with pytest.raises(RuntimeError):
        await asyncio.wait_for(server._start(), timeout=5)

    assert lifecycle.calls == ["shutdown"]


@pytest.mark.asyncio
async def test_an_open_stream_cannot_hold_back_the_shutdown_phase(monkeypatch):
    import socket
    from webfluid.core.fluid.server import Server

    async def stream(scope, receive, send):
        if scope["type"] != "http": return
        await send({"type": "http.response.start", "status": 200, "headers": []})
        while True:
            await send({"type": "http.response.body", "body": b".", "more_body": True})
            await asyncio.sleep(0.1)

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    monkeypatch.setenv("SERVER_PORT", str(port))

    lifecycle = Recorder()
    server = Server(stream, lifecycle)
    task = asyncio.create_task(server._start())
    while server._server is None or not server._server.started: await asyncio.sleep(0.05)

    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(b"GET / HTTP/1.1\r\nHost: test\r\n\r\n")
    await reader.read(1)

    server._server.should_exit = True
    await asyncio.wait_for(task, timeout=9)
    writer.close()

    assert lifecycle.calls == ["startup", "shutdown"]


def _free_port():
    import socket
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


async def _hello(scope, receive, send):
    if scope["type"] != "http": return
    await send({"type": "http.response.start", "status": 200, "headers": [(b"content-length", b"2")]})
    await send({"type": "http.response.body", "body": b"ok"})


async def _get(port):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(b"GET / HTTP/1.1\r\nHost: test\r\nConnection: close\r\n\r\n")
    answer = await reader.read()
    writer.close()
    return answer.split(b"\r\n", 1)[0]


class BusLifecycle(Recorder):
    def __init__(self, bus):
        super().__init__()
        self.bus = bus

    async def run_startup(self):
        self.calls.append("startup")
        self.bus._events.create_pending_loops()


@pytest.fixture
def running_bus(make_fluid, monkeypatch):
    import webfluid.core.ext as ext
    from webfluid.core.fluid import server as module
    from webfluid.extensions.events.main import EventBus

    bus = EventBus(make_fluid())
    monkeypatch.setattr(ext, "events", bus)
    monkeypatch.setattr(module, "EXT_EVENTS", True)
    monkeypatch.setenv("SERVER_PORT", str(_free_port()))
    return bus


async def _serve_until(server, done, timeout=5):
    task = asyncio.create_task(server._start())
    deadline = asyncio.get_running_loop().time() + timeout
    while not done() and asyncio.get_running_loop().time() < deadline: await asyncio.sleep(0.02)
    while server._server is None or not server._server.started: await asyncio.sleep(0.02)
    server._server.should_exit = True
    await asyncio.wait_for(task, timeout=9)


def test_the_bus_declares_server_running_as_an_internal_signal(make_fluid):
    from webfluid.extensions.events.main import EventBus

    bus = EventBus(make_fluid())

    assert bus.has_event(EventBus.SERVER_RUNNING)
    assert bus._events.is_internal(EventBus.SERVER_RUNNING)

    bus.event(EventBus.SERVER_RUNNING)(lambda data: None)
    with pytest.raises(ValueError):
        bus.create_signal(EventBus.SERVER_RUNNING, internal=False)


def test_expanding_the_bus_again_declares_server_running_again(make_fluid):
    from webfluid.extensions.events.main import EventBus

    fluid = make_fluid()
    bus = EventBus(fluid)
    bus.expand_fluid(fluid)

    assert bus.has_event(EventBus.SERVER_RUNNING)
    assert bus._events._pending == [EventBus.SERVER_RUNNING]


@pytest.mark.asyncio
async def test_server_running_follows_startup_and_reaches_a_listening_server(running_bus):
    from webfluid.core.fluid.server import Server
    from webfluid.extensions.events.main import EventBus
    import os

    order, seen = [], []
    lifecycle = BusLifecycle(running_bus)

    @running_bus.event(EventBus.SERVER_RUNNING)
    async def running(data):
        order.append(list(lifecycle.calls))
        seen.append((data, await _get(data["port"])))

    await _serve_until(Server(_hello, lifecycle), lambda: seen)

    assert order == [["startup"]]
    assert len(seen) == 1
    payload, status = seen[0]
    assert status == b"HTTP/1.1 200 OK"
    assert payload["host"] == "127.0.0.1" and payload["port"] == int(os.environ["SERVER_PORT"])
    assert payload["pid"] == os.getpid() and payload["started_at"].endswith("+00:00")
    assert lifecycle.calls == ["startup", "shutdown"]


@pytest.mark.asyncio
async def test_a_server_without_subscribers_announces_without_failing(running_bus, monkeypatch):
    from webfluid.core.fluid.server import Server

    failures = []
    monkeypatch.setattr("webfluid.core.fluid.server.log_factory.exception", lambda *args: failures.append(args))
    lifecycle = BusLifecycle(running_bus)

    server = Server(_hello, lifecycle)
    served = []

    async def probe():
        while server._server is None or not server._server.started: await asyncio.sleep(0.02)
        served.append(await _get(server._server.config.port))

    checker = asyncio.create_task(probe())
    await _serve_until(server, lambda: served)
    await checker

    assert served == [b"HTTP/1.1 200 OK"]
    assert failures == []
    assert lifecycle.calls == ["startup", "shutdown"]


@pytest.mark.asyncio
async def test_a_failing_subscriber_leaves_the_server_and_other_subscribers_running(running_bus):
    from webfluid.core.fluid.server import Server
    from webfluid.extensions.events.main import EventBus

    seen = []

    @running_bus.event(EventBus.SERVER_RUNNING)
    async def broken(data): raise RuntimeError("subscriber failed")

    @running_bus.event(EventBus.SERVER_RUNNING)
    async def healthy(data): seen.append(await _get(data["port"]))

    lifecycle = BusLifecycle(running_bus)
    await _serve_until(Server(_hello, lifecycle), lambda: seen)

    assert seen == [b"HTTP/1.1 200 OK"]
    assert lifecycle.calls == ["startup", "shutdown"]


@pytest.mark.asyncio
async def test_every_serve_announces_once(running_bus, monkeypatch):
    from webfluid.core.fluid.server import Server
    from webfluid.extensions.events.main import EventBus

    seen = []

    @running_bus.event(EventBus.SERVER_RUNNING)
    async def running(data): seen.append(data["started_at"])

    server = Server(_hello, BusLifecycle(running_bus))
    await _serve_until(server, lambda: len(seen) == 1)
    monkeypatch.setenv("SERVER_PORT", str(_free_port()))
    await _serve_until(server, lambda: len(seen) == 2)
    await asyncio.sleep(0.1)

    assert len(seen) == 2 and seen[0] != seen[1]


@pytest.mark.asyncio
async def test_a_server_that_never_starts_announces_nothing(running_bus):
    from webfluid.core.fluid.server import Server
    from webfluid.extensions.events.main import EventBus

    seen = []

    @running_bus.event(EventBus.SERVER_RUNNING)
    async def running(data): seen.append(data)

    server = Server(_hello, BusLifecycle(running_bus))

    async def crash(): raise RuntimeError("address already in use")
    server._lifecycle.run_startup = crash

    with pytest.raises(RuntimeError):
        await asyncio.wait_for(server._start(), timeout=5)
    await asyncio.sleep(0.05)

    assert seen == []


def test_announcing_without_the_event_bus_touches_nothing(monkeypatch):
    import webfluid.core.ext as ext
    from webfluid.core.fluid import server as module
    from webfluid.core.fluid.server import Server

    class Refusing:
        def trigger(self, *args): raise AssertionError("the bus must not be used")

    monkeypatch.setattr(ext, "events", Refusing())
    monkeypatch.setattr(module, "EXT_EVENTS", False)

    Server(_hello, Recorder())._announce("127.0.0.1", 8000)


def test_a_failed_announcement_is_logged_instead_of_raised(monkeypatch):
    import webfluid.core.ext as ext
    from webfluid.core.fluid import server as module
    from webfluid.core.fluid.server import Server

    class Broken:
        def trigger(self, *args): raise ValueError("bus not ready")

    failures = []
    monkeypatch.setattr(ext, "events", Broken())
    monkeypatch.setattr(module, "EXT_EVENTS", True)
    monkeypatch.setattr(module.log_factory, "exception", lambda exc, message=None: failures.append(message))

    Server(_hello, Recorder())._announce("127.0.0.1", 8000)

    assert failures == ["Could not announce 'server:running'."]


@pytest.mark.asyncio
async def test_a_bus_expanded_inside_a_running_loop_delivers_server_running(make_fluid):
    from webfluid.extensions.events.main import EventBus

    bus = EventBus(make_fluid())
    seen = []
    bus.event(EventBus.SERVER_RUNNING)(lambda data: seen.append(data))
    await asyncio.sleep(0)

    bus.trigger(EventBus.SERVER_RUNNING, {"port": 1})
    await asyncio.sleep(0.05)

    assert seen == [{"port": 1}]
