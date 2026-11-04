from starlette.datastructures import Headers
from starlette.requests import Request
import pytest


def test_proxy_removes_all_connection_nominated_headers():
    from webfluid.utils.core.proxy import forwarded_headers
    headers = Headers(raw=[(b"connection", b"X-Internal"), (b"connection", b"X-Other"),
                           (b"x-internal", b"secret"), (b"x-other", b"secret"),
                           (b"proxy-authorization", b"secret"), (b"authorization", b"Bearer test")])
    forwarded = forwarded_headers(headers)
    assert set(forwarded) == {"authorization"}


def test_request_logs_are_private_by_default(make_fluid, monkeypatch):
    from webfluid.core.context import FluidContext
    from webfluid.core.processing.lifecycle import before
    app, hooks, messages = make_fluid(), [], []
    app._request_lifecycle.before.add = hooks.append
    monkeypatch.setattr(before.log_factory, "log", messages.append)
    before.install_request_logger(app)
    request = Request({"type": "http", "method": "GET", "path": "/reset/secret-token",
                       "headers": [(b"user-agent", b"unique-browser\r\nforged")],
                       "query_string": b"token=secret", "client": ("192.0.2.1", 1)})
    with FluidContext(app, request): hooks[0]()
    assert messages == ["[Request] GET"]
    app.config["REQUEST_LOG_USER_AGENT"] = True
    with FluidContext(app, request): hooks[0]()
    assert messages[-1] == "[Request] GET (unique-browser??forged)"


async def test_error_log_context_omits_raw_paths(make_fluid, monkeypatch):
    from webfluid.core.processing.error import handler
    app, messages = make_fluid(), []
    handler.install_error_handler(app)
    monkeypatch.setattr(handler.log_factory, "exception", lambda error, context: messages.append(context))
    request = Request({"type": "http", "method": "GET", "path": "/reset/private-token",
                       "headers": [], "query_string": b""})
    response = await app.exception_handlers[Exception](request, ValueError("failure"))
    assert response.status_code == 500 and messages == ["GET"]


def test_oauth_popup_escapes_script_values_and_prevents_caching():
    from webfluid.extensions.security.services.oauth import OAuthService
    request = Request({"type": "http", "scheme": "https", "path": "/", "headers": [],
                       "server": ("example.org", 443), "query_string": b"", "session": {}})
    response = OAuthService.authorize_response(request, '</script><script>alert(1)</script>', "desktop")
    assert response.body.count(b"</script>") == 1
    assert b"\\u003c/script\\u003e" in response.body
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


@pytest.mark.parametrize("path", ["//evil.example", "/\\evil.example", "/\n/evil.example", "/\t/evil.example"])
def test_oauth_redirect_rejects_browser_normalization_bypasses(path):
    from webfluid.extensions.security.services.oauth import OAuthService
    request = Request({"type": "http", "path": "/", "headers": [], "query_string": b"",
                       "session": {"redirect_path": path}})
    assert OAuthService.authorize_response(request, "provider", "mobile").headers["location"] == "/"


async def test_failed_reference_refresh_cannot_report_old_hashes_as_fresh(monkeypatch, tmp_path):
    from webfluid.utils.integrity import IntegrityReference

    class Reference(IntegrityReference):
        pass

    Reference.setup("widget", "https://example.org/reference", "reference", [], tmp_path)
    monkeypatch.setattr(Reference, "refresh", lambda: {"error": "REFERENCE_UPDATE_FAILED", "commit": "old"})
    monkeypatch.setattr(Reference, "generate", lambda: pytest.fail("must not generate after failed refresh"))
    result = await Reference.compute("failed-fetch")
    assert result["status"] == "unavailable" and result["error"] == "REFERENCE_UPDATE_FAILED"


async def test_async_integrity_hashing_does_not_block_the_event_loop(monkeypatch, tmp_path):
    from webfluid.utils.integrity import Artifact, IntegrityReference
    import threading

    class Reference(IntegrityReference):
        pass

    owner = threading.get_ident()
    artifact = Artifact("widget", tmp_path / "a.js", "/a.js", "Widget")
    Reference.setup("widget", "", "ref", [artifact], tmp_path)

    def digest(self):
        assert threading.get_ident() != owner
        return "0" * 64, 0

    monkeypatch.setattr(Artifact, "digest", digest)
    await Reference.provide({"run": "test"})
    await Reference.status()
