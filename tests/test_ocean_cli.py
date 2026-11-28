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
    def __init__(self, error=None, required=False):
        self.error = error
        self.required = required
        self.released = None
        self.calls = []
        self.fields = []

    def release(self, ptype, package_id, data, checksum, security=False, license=None, prompt=False):
        if self.error: raise self.error
        assert checksum == hashlib.sha256(data).hexdigest()
        self.calls.append((license, prompt))
        if self.required and prompt and license is None: raise OceanError(422, "LICENSE_REQUIRED")
        self.released = (ptype, package_id, security)
        return {"id": package_id, "review_status": None}

    def license_search(self, query):
        return [{"license_id": "MIT", "name": "MIT License"}]

    def license_fields(self, license_id, software, orga):
        self.fields.append((license_id, software, orga))
        return {"fields": [{"key": "year", "label": "Year", "default": "2026"},
                           {"key": "copyright_holder", "label": "Copyright holder", "default": "Maker"}]}


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


def _license_answers(monkeypatch, values):
    queue = list(values)
    monkeypatch.setitem(publish.questions.__dict__, "ocean_license_query", SimpleNamespace(ask=lambda: "mit"))
    monkeypatch.setitem(publish.questions.__dict__, "ocean_license_choice",
                        lambda _matches: SimpleNamespace(ask=lambda: "MIT"))
    monkeypatch.setitem(publish.questions.__dict__, "ocean_license_value",
                        lambda _label, default: SimpleNamespace(ask=lambda: queue.pop(0) if queue else default))


def test_a_release_with_its_own_license_is_never_asked_for_one(monkeypatch):
    _confirm(monkeypatch)
    hub, data = _Publisher(), _archive()
    package = {"actions": ["publish"], "releases": [], "license_missing": True}
    publish._release(hub, "additives", "demo", package, data, hashlib.sha256(data).hexdigest(), "1.1", False, True)
    assert hub.calls == [(None, False)] and hub.fields == []


def test_a_release_without_license_of_an_unlicensed_package_asks_first(monkeypatch):
    _confirm(monkeypatch)
    _license_answers(monkeypatch, ["2025", " ACME "])
    hub, data = _Publisher(), _archive()
    package = {"actions": ["publish"], "releases": [], "license_missing": True, "oid": 4}
    publish._release(hub, "additives", "demo", package, data, hashlib.sha256(data).hexdigest(), "1.1", False, False)
    assert hub.fields == [("MIT", "demo", 4)]
    assert hub.calls == [({"license_id": "MIT", "values": {"year": "2025", "copyright_holder": "ACME"}}, True)]


def test_a_release_the_registry_refuses_without_license_asks_and_retries(monkeypatch):
    _confirm(monkeypatch)
    _license_answers(monkeypatch, [])
    hub, data = _Publisher(required=True), _archive()
    package = {"actions": ["publish"], "releases": [], "license_missing": False}
    publish._release(hub, "additives", "demo", package, data, hashlib.sha256(data).hexdigest(), "1.1", False, False)
    assert hub.calls[0] == (None, True)
    assert hub.calls[1] == ({"license_id": "MIT", "values": {"year": "2026", "copyright_holder": "Maker"}}, True)
    assert hub.released == ("additives", "demo", False)


def test_a_declined_license_choice_uploads_nothing(monkeypatch):
    _confirm(monkeypatch)
    monkeypatch.setitem(publish.questions.__dict__, "ocean_license_query", SimpleNamespace(ask=lambda: None))
    hub, data = _Publisher(), _archive()
    package = {"actions": ["publish"], "releases": [], "license_missing": True}
    with pytest.raises(typer.Exit):
        publish._release(hub, "additives", "demo", package, data, hashlib.sha256(data).hexdigest(), "1.1", False,
                         False)
    assert hub.calls == []


@pytest.mark.parametrize("selected,ships", [
    (["LICENSE", "manifest.json"], True), (["COPYING.txt"], True), (["licence.md"], True),
    (["docs/LICENSE", "manifest.json"], False), (["manifest.json"], False)
])
def test_only_a_root_license_file_counts_as_shipped(selected, ships):
    assert publish._ships_license(selected) is ships

