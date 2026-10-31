import pytest


class _Process:
    def __init__(self, code=None):
        self.returncode = code
        self.pid = 4242

    def poll(self):
        return self.returncode


class _Log:
    def __init__(self):
        self.warnings = []

    def warning(self, message):
        self.warnings.append(message)


@pytest.fixture
def dev(monkeypatch):
    from webfluid.surface.frontend.vite import dev

    spawned = []

    def spawn(*_, **__):
        process = _Process()
        spawned.append(process)
        return process

    log = _Log()
    monkeypatch.setattr(dev, "node_proc", spawn)
    monkeypatch.setattr(dev, "log_factory", log)
    monkeypatch.setattr(dev, "root", ".")
    monkeypatch.setattr(dev, "stopping", False)
    monkeypatch.setattr(dev, "failures", 0)
    monkeypatch.setattr(dev, "started", 0.0)
    monkeypatch.setattr(dev, "proc", None)
    dev.start()
    return dev, spawned, log


def test_a_running_dev_server_is_left_alone(dev):
    module, spawned, log = dev
    module.watch()
    assert len(spawned) == 1 and log.warnings == []


def test_a_stopped_dev_server_is_restarted_with_a_warning(dev, monkeypatch):
    module, spawned, log = dev
    spawned[-1].returncode = 1
    monkeypatch.setattr(module, "started", -1000.0)

    module.watch()

    assert len(spawned) == 2 and module.proc is spawned[-1]
    assert len(log.warnings) == 1 and "Restarting" in log.warnings[0]


def test_a_dev_server_that_keeps_dying_is_given_up(dev):
    module, spawned, log = dev
    for _ in range(module.max_failures + 2):
        spawned[-1].returncode = 1
        module.watch()

    assert len(spawned) == module.max_failures
    assert "no longer restarted" in log.warnings[-1]
    assert len(log.warnings) == module.max_failures


def test_a_stopping_app_does_not_restart_the_dev_server(dev, monkeypatch):
    module, spawned, log = dev
    spawned[-1].returncode = 0
    monkeypatch.setattr(module, "stopping", True)
    module.watch()
    assert len(spawned) == 1 and log.warnings == []


def test_without_scheduling_the_dev_server_runs_unsupervised_with_a_warning(dev, monkeypatch):
    module, _, log = dev
    monkeypatch.setattr(module, "EXT_SCHEDULING", False)
    module.supervise()
    assert len(log.warnings) == 1 and "EXT_SCHEDULING" in log.warnings[0]


def test_with_scheduling_a_watchdog_job_is_registered(dev, monkeypatch):
    from webfluid.core import ext

    module, _, log = dev
    jobs = []

    class _Scheduler:
        def add_job(self, fn, trigger, **kwargs):
            jobs.append((fn, trigger, kwargs))

    monkeypatch.setattr(module, "EXT_SCHEDULING", True)
    monkeypatch.setattr(ext, "scheduler", _Scheduler())
    module.supervise()

    assert log.warnings == []
    fn, trigger, kwargs = jobs[0]
    assert fn is module.watch and kwargs["id"] == module.watch_job and kwargs["replace_existing"]
    assert trigger.interval.total_seconds() == module.watch_interval
