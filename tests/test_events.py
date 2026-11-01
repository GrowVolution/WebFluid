import asyncio, pytest

from webfluid.exceptions import FrameworkException
from webfluid.extensions.events.events import Events
from webfluid.extensions.events.loop import LoopManager
from webfluid.extensions.events.queries import Queries


def decorator(fn):
    async def wrapper(event, data): return await fn(data)
    return wrapper


@pytest.fixture
def events():
    manager = Events(queue_size=10, ctx_decorator=decorator)
    manager.create_loop = LoopManager(manager, None).create_loop
    return manager


def test_registering_outside_a_running_loop_is_deferred(events):
    events.create_signal("ping")

    assert events._pending == ["ping"]
    assert events.has_event("ping")


def test_a_deferred_event_is_wired_up_once_the_loop_starts(events):
    received = []

    @events.event("ping")
    async def on_ping(data): received.append(data)

    assert events._pending == ["ping"]

    async def run():
        events.create_pending_loops()
        await asyncio.sleep(0)

        events.trigger("ping", {"hello": "world"})
        await asyncio.sleep(0.05)

    asyncio.run(run())
    assert received == [{"hello": "world"}]


def test_create_pending_loops_is_idempotent(events):
    async def run():
        events.create_signal("ping")
        events.create_pending_loops()
        await asyncio.sleep(0)
        events.create_pending_loops()

    asyncio.run(run())
    assert events._pending is None


def test_registering_a_new_event_off_loop_after_startup_raises(events):
    events.create_pending_loops()

    with pytest.raises(FrameworkException):
        events.create_signal("late")


def test_a_refused_late_registration_leaves_nothing_behind(events):
    events.create_pending_loops()

    with pytest.raises(FrameworkException):
        events.create_signal("late")

    assert not events.has_event("late") and "late" not in events._events


def test_the_consumer_loop_does_not_inherit_the_registering_context(events):
    import contextvars
    request = contextvars.ContextVar("request", default=None)
    seen = []

    async def run():
        manager = LoopManager(events, None)

        async def loop(event): seen.append(request.get())
        manager._loop = loop

        request.set("pinned")
        await manager.create_loop("ping")

    asyncio.run(run())
    assert seen == [None]


def test_the_bus_answers_whether_a_contract_exists(make_fluid):
    from webfluid.extensions.events.main import EventBus

    bus = EventBus(make_fluid())

    bus.create_signal("public_signal", internal=False)
    bus.query("answerable")(lambda data: None)

    assert bus.has_event("public_signal") is True
    assert bus.has_event("never_registered") is False
    assert bus.has_query("answerable") is True
    assert bus.has_query("never_registered") is False


def test_the_bus_refuses_introspection_before_it_is_expanded():
    from webfluid.extensions.events.main import EventBus

    with pytest.raises(FrameworkException):
        EventBus().has_query("anything")


@pytest.mark.asyncio
async def test_collectors_can_isolate_failures_without_changing_default_query_errors():
    queries = Queries(decorator)

    @queries.query("collector", singleton=False)
    async def broken(data): raise RuntimeError("contributor failed")

    @queries.query("collector", singleton=False)
    async def healthy(data): return {"value": data}

    results = await queries.request("collector", 42, return_exceptions=True)
    assert isinstance(results[0], RuntimeError)
    assert results[1] == {"value": 42}
    with pytest.raises(RuntimeError, match="contributor failed"):
        await queries.request("collector", 42)
