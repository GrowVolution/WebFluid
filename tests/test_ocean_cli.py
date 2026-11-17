from importlib import import_module
from types import SimpleNamespace
import hashlib

import pytest
import typer

from webfluid.exceptions import OceanError

install = import_module("webfluid.cli.ocean.install")
publish = import_module("webfluid.cli.ocean.publish")


def _archive():
    from webfluid.cli.ocean.archive import _pack
    return _pack([("manifest.json", b"{}")])


class _Ocean:
    authenticated = True

    def __init__(self, meta, statements=(), waive_error=None):
        self.meta = meta
        self.statements = list(statements)
        self.waive_error = waive_error
        self.waived = None
        self.downloads = []
        self.data = _archive()

    def resolve(self, *_):
        return self.meta

    def waiver(self, *_):
        return {"required": True, "hint": "Read the terms.", "statements": self.statements}

    def waive(self, _ptype, _pid, accepted):
        if self.waive_error: raise self.waive_error
        self.waived = list(accepted)

    def download(self, _ptype, _pid, version):
        self.downloads.append(version)
        return self.data

    def integrity(self, *_):
        raise OceanError(404, "Not Found")


def _answers(monkeypatch, values):
    queue = list(values)
    monkeypatch.setitem(install.questions.__dict__, "ocean_confirm_waiver",
                        lambda _text: SimpleNamespace(ask=lambda: queue.pop(0)))


def _paid(**changes):
    meta = {"oss": False, "owned": True, "waiver_required": True, "withdrawal_pending": False,
            "releases": [{"version": "1.1.0", "available": True}, {"version": "1.0.0", "available": True}]}
    meta.update(changes)
    return meta


STATEMENTS = [{"id": "notice", "text": "Notice", "required": True},
              {"id": "consent", "text": "Consent", "required": True},
              {"id": "newsletter", "text": "Optional", "required": False}]


def test_every_required_statement_must_be_confirmed_before_a_paid_download(monkeypatch, tmp_path):
    ocean = _Ocean(_paid(), STATEMENTS)
    _answers(monkeypatch, [True, False])
    assert install._install_package(ocean, "additives", "demo", None, "", False, tmp_path / "demo") is False
    assert ocean.waived is None and ocean.downloads == []


def test_optional_statements_may_be_declined_and_only_accepted_ids_are_sent(monkeypatch, tmp_path):
    ocean = _Ocean(_paid(), STATEMENTS)
    _answers(monkeypatch, [True, True, False])
    assert install._install_package(ocean, "additives", "demo", None, "", False, tmp_path / "demo") is True
    assert ocean.waived == ["notice", "consent"] and ocean.downloads == ["1.1.0"]


def test_a_refused_waiver_stops_the_download(monkeypatch, tmp_path):
    ocean = _Ocean(_paid(), STATEMENTS[:2], waive_error=OceanError(422, "WAIVER_INCOMPLETE"))
    _answers(monkeypatch, [True, True])
    assert install._install_package(ocean, "additives", "demo", None, "", False, tmp_path / "demo") is False
    assert ocean.downloads == []


@pytest.mark.parametrize("meta,installed", [
    (_paid(withdrawal_pending=True), False),
    (_paid(withdrawal_pending=True, waiver_required=False,
           releases=[{"version": "1.1.0", "available": False}, {"version": "1.0.0", "available": True}]), True),
    (_paid(withdrawal_pending=True, waiver_required=False,
           releases=[{"version": "1.0.0", "available": False}]), False),
])
def test_a_pending_withdrawal_pauses_exactly_what_the_registry_pauses(monkeypatch, tmp_path, meta, installed):
    ocean = _Ocean(meta)
    _answers(monkeypatch, [])
    assert install._install_package(ocean, "additives", "demo", None, "", False, tmp_path / "demo") is installed
    assert ocean.downloads == (["1.0.0"] if installed else [])


class _Publisher:
    def __init__(self, error=None):
        self.error = error
        self.released = None

    def release(self, ptype, package_id, data, checksum, security=False):
        if self.error: raise self.error
        assert checksum == hashlib.sha256(data).hexdigest()
        self.released = (ptype, package_id, security)
        return {"id": package_id, "review_status": None}


def _confirm(monkeypatch, value=True):
    monkeypatch.setitem(publish.questions.__dict__, "ocean_confirm_release",
                        lambda *_: SimpleNamespace(ask=lambda: value))


def test_publishing_an_existing_package_uploads_a_release(monkeypatch):
    _confirm(monkeypatch)
    hub, data = _Publisher(), _archive()
    package = {"actions": ["read", "publish"], "releases": [{"version": "1.0"}]}
    publish._release(hub, "additives", "demo", package, data, hashlib.sha256(data).hexdigest(), "1.1", True)
    assert hub.released == ("additives", "demo", True)


@pytest.mark.parametrize("package,version", [
    ({"actions": ["read"], "releases": []}, "1.1"),
    ({"actions": ["publish"], "releases": [{"version": "1.1"}]}, "1.1")
])
def test_a_release_without_rights_or_with_a_taken_version_is_refused_locally(monkeypatch, package, version):
    _confirm(monkeypatch)
    hub, data = _Publisher(), _archive()
    with pytest.raises(typer.Exit):
        publish._release(hub, "additives", "demo", package, data, "x", version, False)
    assert hub.released is None


def test_a_refused_release_reports_the_registry_reason(monkeypatch, capsys):
    _confirm(monkeypatch)
    hub, data = _Publisher(OceanError(409, "REVIEW_PENDING")), _archive()
    with pytest.raises(typer.Exit):
        publish._release(hub, "additives", "demo", {"actions": ["publish"], "releases": []}, data,
                         hashlib.sha256(data).hexdigest(), "1.1", False)
    assert "under review" in capsys.readouterr().out
