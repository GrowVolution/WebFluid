from types import SimpleNamespace
import smtplib, pytest

from webfluid.core.config.default import DefaultConfig
from webfluid.exceptions import FrameworkException
from webfluid.extensions.mailman.main import Mail
from webfluid.extensions.mailman.sync import SyncManager

SETTINGS = ("smtp.example.org", 465, True, False, 10, None, None, "noreply@example.org")


class Recorder:
    opened = []

    def __init__(self, host=None, port=None, timeout=None):
        Recorder.opened.append((type(self).__name__, host, port))
        self.started = False

    def starttls(self): self.started = True
    def quit(self): pass


class Plain(Recorder): pass
class Implicit(Recorder): pass


@pytest.fixture
def smtp(monkeypatch):
    Recorder.opened = []
    monkeypatch.setattr(smtplib, "SMTP", Plain)
    monkeypatch.setattr(smtplib, "SMTP_SSL", Implicit)
    return Recorder


def test_implicit_tls_opens_an_ssl_connection(smtp):
    with SyncManager(*SETTINGS).client() as client:
        assert client.started is False

    assert smtp.opened == [("Implicit", "smtp.example.org", 465)]


def test_starttls_upgrades_a_plain_connection(smtp):
    host, _, _, _, timeout, user, password, sender = SETTINGS
    manager = SyncManager(host, 587, False, True, timeout, user, password, sender)

    with manager.client() as client:
        assert client.started is True

    assert smtp.opened == [("Plain", "smtp.example.org", 587)]


def test_the_shipped_defaults_pair_starttls_with_the_submission_port():
    assert DefaultConfig.MAIL_PORT == 587
    assert DefaultConfig.MAIL_USE_TLS is False
    assert DefaultConfig.MAIL_USE_STARTTLS is True


def test_both_tls_flags_at_once_are_rejected():
    config = {
        "MAIL_SERVER": "smtp.example.org", "MAIL_PORT": 587,
        "MAIL_USE_TLS": True, "MAIL_USE_STARTTLS": True,
        "MAIL_TIMEOUT": 10, "MAIL_USERNAME": None, "MAIL_PASSWORD": None,
        "MAIL_DEFAULT_SENDER": "noreply@example.org"
    }

    with pytest.raises(FrameworkException):
        Mail().expand_fluid(SimpleNamespace(config=config))


def test_a_failing_login_is_reported_as_a_framework_error(smtp, monkeypatch):
    def login(self, user, password):
        raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    monkeypatch.setattr(Plain, "login", login, raising=False)
    host, _, _, _, timeout, _, _, sender = SETTINGS
    manager = SyncManager(host, 587, False, False, timeout, "user", "pw", sender)

    with pytest.raises(FrameworkException):
        with manager.client(): pass


def test_a_failing_connect_is_reported_as_a_framework_error(smtp, monkeypatch):
    def connect(self, host=None, port=None, timeout=None):
        raise smtplib.SMTPConnectError(421, b"no greeting")

    monkeypatch.setattr(Implicit, "__init__", connect)

    with pytest.raises(FrameworkException):
        with SyncManager(*SETTINGS).client(): pass


def test_a_detached_send_reports_its_failure(smtp, monkeypatch):
    logged = []
    monkeypatch.setattr(
        "webfluid.extensions.mailman.sync.log_factory.exception",
        lambda exc, message=None: logged.append((type(exc), message))
    )

    def connect(self, host=None, port=None, timeout=None):
        raise smtplib.SMTPConnectError(421, b"no greeting")

    monkeypatch.setattr(Implicit, "__init__", connect)

    manager = SyncManager(*SETTINGS)
    manager._send_detached(object())

    assert logged and logged[0][0] is FrameworkException


def test_a_detached_send_does_not_raise_into_its_thread(smtp, monkeypatch):
    import threading

    def connect(self, host=None, port=None, timeout=None):
        raise smtplib.SMTPConnectError(421, b"no greeting")

    monkeypatch.setattr(Implicit, "__init__", connect)
    monkeypatch.setattr(
        "webfluid.extensions.mailman.sync.log_factory.exception",
        lambda exc, message=None: None
    )

    failures = []
    monkeypatch.setattr(
        threading, "excepthook", lambda args: failures.append(args)
    )

    before = set(threading.enumerate())
    SyncManager(*SETTINGS).send("to@example.org", "subject", { "plain": "body" })

    for thread in set(threading.enumerate()) - before: thread.join(timeout=5)

    assert failures == []


@pytest.mark.parametrize("kind", ["pdf", "application/pdf"])
def test_attachments_wrap_the_alternative_body_in_a_mixed_message(kind):
    from webfluid.extensions.mailman.message import make_message
    message = make_message("noreply@example.org", "a@example.org", "Subject", {"plain": "Hi", "html": "<p>Hi</p>"},
                           [{"bytes": b"%PDF-1.4", "type": kind, "filename": "contract.pdf"}])
    assert message.get_content_type() == "multipart/mixed"
    body, attachment = message.get_payload()
    assert body.get_content_type() == "multipart/alternative"
    assert [part.get_content_type() for part in body.get_payload()] == ["text/plain", "text/html"]
    assert attachment.get_content_type() == "application/pdf"
    assert attachment.get_filename() == "contract.pdf"
    assert attachment.get_payload(decode=True) == b"%PDF-1.4"


def test_a_message_without_attachments_stays_alternative():
    from webfluid.extensions.mailman.message import make_message
    message = make_message("noreply@example.org", "a@example.org", "Subject", {"plain": "Hi", "html": "<p>Hi</p>"})
    assert message.get_content_type() == "multipart/alternative"
