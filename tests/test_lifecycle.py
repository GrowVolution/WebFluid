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
