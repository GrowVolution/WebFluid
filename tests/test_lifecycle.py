import pytest

from webfluid.core.lifecycle import (
    AdditiveLifecycle, FluidLifecycle, Phase, RequestLifecycle
)


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
