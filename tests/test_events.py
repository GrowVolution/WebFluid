import asyncio, pytest

from webfluid.exceptions import FrameworkException
from webfluid.extensions.events.events import Events
from webfluid.extensions.events.loop import LoopManager


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
