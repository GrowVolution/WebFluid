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
