import pytest

from webfluid.extensions.cache.main import Cache
from webfluid.extensions.cache.legacy import LegacyCache
from webfluid.exceptions import FrameworkException


class FakeFluid:
    def __init__(self, **config):
        self.config = {
            "CACHE_TYPE": "legacy",
            "CACHE_DEFAULT_TIMEOUT": 300,
            "CACHE_REDIS_URI": "redis://localhost:6379/2"
        }
        self.config.update(config)


def test_legacy_cache_expires_without_a_scheduler(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(
        "webfluid.extensions.cache.legacy.monotonic", lambda: now[0]
    )

    cache = LegacyCache(FakeFluid())
    cache.set("key", "value", timeout=10)
    assert cache.get("key") == "value"

    now[0] += 11
    assert cache.get("key") is None


def test_legacy_cache_sweeps_expired_entries(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(
        "webfluid.extensions.cache.legacy.monotonic", lambda: now[0]
    )

    cache = LegacyCache(FakeFluid())
    for i in range(50): cache.set(f"key{i}", i, timeout=5)

    now[0] += 6
    cache.set("fresh", "value", timeout=100)

    assert len(cache._cache) == 1
    assert cache.get("fresh") == "value"


def test_legacy_cache_keeps_refreshed_entries(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(
        "webfluid.extensions.cache.legacy.monotonic", lambda: now[0]
    )

    cache = LegacyCache(FakeFluid())
    cache.set("key", "old", timeout=5)
    cache.set("key", "new", timeout=100)

    now[0] += 6
    cache.set("other", "value")

    assert cache.get("key") == "new"


async def test_legacy_cache_async_api(monkeypatch):
    cache = LegacyCache(FakeFluid())

    await cache.aset("key", "value")
    assert await cache.aget("key") == "value"

    await cache.adelete("key")
    assert await cache.aget("key") is None


def test_cache_selects_the_backend_lazily():
    cache = Cache(FakeFluid())
    assert type(cache.backend).__name__ == "LegacyCache"


def test_cache_rejects_unknown_backends():
    with pytest.raises(ValueError): Cache(FakeFluid(CACHE_TYPE="nope"))


def test_cache_requires_configuration():
    with pytest.raises(FrameworkException): Cache().get("key")
