from starlette.requests import Request
from uuid import uuid4
import jwt, os, pytest

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
    (root / "dist").mkdir(parents=True)
    (root / "dist" / "asset.js").write_text("ok", encoding="utf-8")
    (root / "package.json").write_text("{}", encoding="utf-8")

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
async def test_production_never_serves_the_frontend_workspace(frontend):
    catch = asset_catch(frontend, NAMESPACES)
    response = await catch(_request("vite_ns=webfluid/frontend"), "package.json")

    assert response.status_code == 404


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
    assert contained(frontend, "webfluid/frontend", "dist", "asset.js") is not None
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


@pytest.mark.parametrize("header", [
    b"host", b"content-length", b"transfer-encoding",
    b"connection", b"keep-alive", b"upgrade", b"expect"
])
def test_a_proxied_request_drops_hop_by_hop_headers(header):
    from webfluid.utils.core.proxy import forwarded_headers

    request = Request({
        "type": "http", "method": "POST", "path": "/",
        "headers": [(header, b"value"), (b"authorization", b"Bearer t")],
        "query_string": b""
    })
    forwarded = forwarded_headers(request.headers)

    assert header.decode() not in forwarded
    assert forwarded["authorization"] == "Bearer t"


@pytest.mark.parametrize("pid", [
    "", ".", "..", "../users", "a/b", "C:" + chr(92) + "users", "a:b"
])
def test_a_package_id_that_is_not_a_directory_name_is_refused(pid):
    from importlib import import_module
    install = import_module("webfluid.cli.ocean.install")

    assert install._usable_id(pid) is False


@pytest.mark.parametrize("pid", ["users", "users-admin", "stripe_connect"])
def test_a_plain_package_id_stays_usable(pid):
    from importlib import import_module
    install = import_module("webfluid.cli.ocean.install")

    assert install._usable_id(pid) is True


@pytest.fixture
def ocean_token(tmp_path, monkeypatch):
    from webfluid.utils import ocean

    target = tmp_path / ".wf-ocean"
    monkeypatch.setattr(ocean, "TOKEN_FILE", target)
    return ocean, target


def test_the_ocean_token_survives_a_round_trip(ocean_token):
    ocean, _ = ocean_token
    ocean.save_token("  secret-token  ")

    assert ocean.load_token() == "secret-token"


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes only")
def test_the_ocean_token_is_written_for_its_owner_only(ocean_token):
    ocean, target = ocean_token
    target.write_text("loose", encoding="utf-8")
    target.chmod(0o644)
    ocean.save_token("secret-token")

    assert target.stat().st_mode & 0o077 == 0


@pytest.mark.parametrize("stored", ["", "not-a-hash", "$argon2id$v=19$broken"])
def test_a_hash_the_hasher_cannot_read_fails_the_check(stored):
    from webfluid.extensions.security.services.hashing import HashService

    service = HashService(1, 8, 1, threads=1)

    assert service.verify(stored, "whatever") is False


@pytest.mark.asyncio
@pytest.mark.parametrize("requirement, field", [
    ("has_roles", "roles"), ("has_any_role", "roles"),
    ("has_permissions", "permissions"), ("has_any_permission", "permissions")
])
@pytest.mark.parametrize("value", [[], None, "admin"])
async def test_a_requirement_without_a_usable_list_is_refused(requirement, field, value):
    from webfluid.extensions.security.services.user.gating.check import check_requirement

    with pytest.raises(ValueError, match=field):
        await check_requirement(object(), { "requirement": requirement, field: value })


@pytest.mark.asyncio
@pytest.mark.parametrize("r", [
    { "requirement": "is_admin" }, { "requirement": "has_2fa" },
    { "requirement": "has_roles", "roles": ["staff"] }
])
async def test_a_requirement_beyond_sign_in_fails_closed_without_a_user(r):
    from webfluid.extensions.security.services.user.gating.check import check_requirement

    assert await check_requirement(None, r) is False


def test_the_request_logger_survives_a_client_less_scope(make_fluid):
    from webfluid.core.context import FluidContext
    from webfluid.core.processing.lifecycle.before import install_request_logger

    fluid = make_fluid()
    hooks = []
    fluid._request_lifecycle.before.add = hooks.append
    install_request_logger(fluid)

    request = Request({
        "type": "http", "method": "GET", "path": "/",
        "headers": [], "query_string": b""
    })
    with FluidContext(fluid, request): hooks[0]()
