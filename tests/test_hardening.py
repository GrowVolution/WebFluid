from starlette.requests import Request
from uuid import uuid4
import jwt, pytest

from webfluid.extensions.jwt.config import JWTConfig
from webfluid.extensions.jwt.decode import _kid
from webfluid.extensions.security.services.oauth import _local_path
from webfluid.surface.frontend.vite.assets import asset_catch, contained

NAMESPACES = frozenset({"webfluid/frontend"})


def _request(cookie=None, path="/asset.js"):
    headers = [(b"cookie", cookie.encode())] if cookie is not None else []
    return Request({
        "type": "http", "method": "GET", "path": path,
        "headers": headers, "query_string": b""
    })


@pytest.fixture
def frontend(tmp_path):
    root = tmp_path / "webfluid" / "frontend"
    root.mkdir(parents=True)
    (root / "asset.js").write_text("ok", encoding="utf-8")

    (tmp_path / "app_configs").mkdir()
    (tmp_path / "app_configs" / "app.ini").write_text(
        "[app]\nSECRET_KEY = leaked\n", encoding="utf-8"
    )
    (tmp_path.parent / "outside.ini").write_text("nope", encoding="utf-8")

    return tmp_path


@pytest.mark.asyncio
async def test_a_known_namespace_serves_its_own_asset(frontend):
    catch = asset_catch(frontend, NAMESPACES)
    response = await catch(_request("vite_ns=webfluid/frontend"), "asset.js")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_an_empty_namespace_cannot_read_the_project_root(frontend):
    catch = asset_catch(frontend, NAMESPACES)
    response = await catch(
        _request("vite_ns="), "app_configs/app.ini"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_a_missing_namespace_cookie_is_refused(frontend):
    catch = asset_catch(frontend, NAMESPACES)
    response = await catch(_request(), "app_configs/app.ini")

    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("namespace", [
    "..", "../..", "webfluid/frontend/../..", "/etc"
])
async def test_a_traversing_namespace_is_refused(frontend, namespace):
    catch = asset_catch(frontend, NAMESPACES)
    response = await catch(
        _request(f"vite_ns={namespace}"), "app_configs/app.ini"
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_a_traversing_path_cannot_escape_the_namespace(frontend):
    catch = asset_catch(frontend, NAMESPACES)
    response = await catch(
        _request("vite_ns=webfluid/frontend"), "../../outside.ini"
    )

    assert response.status_code == 404


def test_contained_refuses_anything_outside_the_root(frontend):
    assert contained(frontend, "webfluid/frontend", "asset.js") is not None
    assert contained(frontend, "..", "outside.ini") is None
    assert contained(frontend, "webfluid") is None


def _config():
    return JWTConfig({
        "JWT_ROTARY_INTERVAL": 15,
        "JWT_SECRET_LENGTH": 128,
        "JWT_EXPIRY_DAYS": 30,
        "JWT_ALGORITHM": "HS256",
        "JWT_ISSUER": "tests",
        "JWT_AUDIENCES": { "default": "Application" }
    })


def test_a_real_key_id_is_accepted():
    kid = uuid4().hex
    token = jwt.encode(
        { "sub": "1" }, "k" * 40, headers={ "kid": kid }, algorithm="HS256"
    )

    assert _kid(token) == kid


def test_a_token_without_a_key_id_falls_back():
    token = jwt.encode({ "sub": "1" }, "k" * 40, algorithm="HS256")

    assert _kid(token) is None


@pytest.mark.parametrize("kid", [
    "current", "revoked:1", "../current", "",
    uuid4().hex.upper(), uuid4().hex + "x"
])
def test_a_key_id_outside_the_key_namespace_is_rejected(kid):
    token = jwt.encode(
        { "sub": "1" }, "k" * 40, headers={ "kid": kid }, algorithm="HS256"
    )

    with pytest.raises(jwt.InvalidTokenError):
        _kid(token)


@pytest.mark.parametrize("target", [
    "https://evil.example", "//evil.example", "/\\evil.example",
    "http://evil.example/path", "evil.example", None, 1
])
def test_an_offsite_redirect_is_refused(target):
    assert _local_path(target) == "/"


@pytest.mark.parametrize("target", ["/", "/dashboard", "/a/b?c=d"])
def test_a_local_redirect_survives(target):
    assert _local_path(target) == target


@pytest.mark.parametrize("header", [b"x_forwarded_for", b"x-forwarded-for"])
def test_the_rate_limit_key_ignores_forwarded_headers(make_fluid, header):
    fluid = make_fluid()
    key_func = fluid._limiter.limiter._key_func

    request = Request({
        "type": "http", "method": "GET", "path": "/",
        "headers": [(header, b"9.9.9.9")], "query_string": b"",
        "client": ("10.0.0.1", 1234)
    })

    assert key_func(request) == "10.0.0.1"


@pytest.mark.asyncio
async def test_disposing_releases_every_engine():
    from webfluid.extensions.sqlalchemy.bind import Bind

    bind = Bind("default", ("sqlite://", "sqlite+aiosqlite://"))
    assert bind.sync_engine is not None
    assert bind.async_engine is not None

    await bind.dispose()
    assert bind._sync is None and bind._async is None


@pytest.mark.asyncio
async def test_disposing_twice_is_a_no_op():
    from webfluid.extensions.sqlalchemy.bind import Bind

    bind = Bind("default", ("sqlite://", "sqlite+aiosqlite://"))
    await bind.dispose()
    await bind.dispose()

    assert bind._sync is None and bind._async is None


@pytest.fixture
def tokens(monkeypatch):
    from types import SimpleNamespace
    from webfluid.extensions.security.services import token as module

    monkeypatch.setattr(
        module, "scheduler", SimpleNamespace(add_job=lambda *a, **k: None)
    )
    return module.TokenService("secret", 3600, "csrf_token", True)


def _csrf_request(cookie, header, session):
    return Request({
        "type": "http", "method": "POST", "path": "/",
        "headers": [
            (b"cookie", f"csrf_token={cookie}".encode()),
            (b"x-csrf-token", header.encode())
        ],
        "query_string": b"", "session": { "csrf_token": session }
    })


@pytest.mark.asyncio
async def test_a_matching_csrf_triple_passes(tokens):
    signed = tokens.generate_token({ "csrf": "raw" })

    assert await tokens.csrf_protect_fn(
        _csrf_request(signed, signed, "raw")
    ) is None


@pytest.mark.asyncio
async def test_a_mismatched_csrf_token_is_refused(tokens):
    signed = tokens.generate_token({ "csrf": "raw" })
    other = tokens.generate_token({ "csrf": "different" })

    with pytest.raises(Exception) as exc:
        await tokens.csrf_protect_fn(_csrf_request(signed, other, "raw"))

    assert exc.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", ["a string", 42, ["a", "list"]])
async def test_a_csrf_token_of_the_wrong_shape_is_refused(tokens, payload):
    signed = tokens.generate_token(payload)

    with pytest.raises(Exception) as exc:
        await tokens.csrf_protect_fn(_csrf_request(signed, signed, "raw"))

    assert exc.value.status_code == 403
    assert exc.value.detail == "INVALID_CSRF"


@pytest.mark.asyncio
async def test_an_unsigned_csrf_token_is_refused(tokens):
    with pytest.raises(Exception) as exc:
        await tokens.csrf_protect_fn(_csrf_request("garbage", "garbage", "raw"))

    assert exc.value.status_code == 403
    assert exc.value.detail == "INVALID_TOKEN"
