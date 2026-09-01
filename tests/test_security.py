import os, pytest

os.environ.setdefault("EXT_SQLALCHEMY", "1")

from sqlalchemy import event, select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from webfluid.core.ext import db
from webfluid.extensions.security.models.user import (
    Permission, Role, User, user_roles
)
from webfluid.extensions.security.services.hashing import HashService
from webfluid.extensions.security.services.user.gating.requirements import admin
from webfluid.extensions.security.utils import PasswordPolicy
from webfluid.extensions.sqlalchemy.executor import AsyncExecutor
from webfluid.extensions.sqlalchemy.main import SQLAlchemy

MEMBERS = 200


@pytest.fixture
async def seeded():
    SQLAlchemy._instance = db
    engine = create_async_engine("sqlite+aiosqlite://")
    queries = []

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def record(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append(statement)

    async with engine.begin() as conn:
        await conn.run_sync(db.Model.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        role = Role("member")
        role.is_admin = True
        for name in ("read", "write"): role.permissions.append(Permission(name))

        for i in range(MEMBERS):
            user = User(f"user{i}", f"u{i}@example.org")
            user.roles.append(role)
            session.add(user)

        await session.commit()

    yield maker, queries
    await engine.dispose()


async def test_admin_gate_uses_a_single_query(seeded):
    maker, queries = seeded

    async with maker() as session:
        user = (await session.execute(
            select(User).where(User.id == 1)
        )).scalars().first()

        queries.clear()
        with AsyncExecutor(session):
            assert await admin.requirement_fulfilled(user) is True

    assert len(queries) == 1
    assert "EXISTS" in queries[0].upper()


async def test_role_membership_never_fans_out(seeded):
    maker, _ = seeded

    async with maker() as session:
        role = (await session.execute(
            select(Role).where(Role.is_admin == True)
        )).scalars().first()

        with pytest.raises(InvalidRequestError): len(role.users)
        with pytest.raises(InvalidRequestError): len(role.permissions)


async def test_loading_a_user_stays_bounded(seeded):
    maker, queries = seeded

    async with maker() as session:
        queries.clear()
        user = (await session.execute(
            select(User).where(User.id == 1)
        )).scalars().first()

    assert user.username == "user0"
    assert len(queries) == 3


async def test_two_fa_relationships_survive_expunging(seeded):
    maker, _ = seeded

    async with maker() as session:
        user = (await session.execute(
            select(User).where(User.id == 1)
        )).scalars().first()
        session.expunge(user)

    assert user.totp_secret is None
    assert user.webauthn_credentials == []


@pytest.mark.parametrize("name", ["identities", "roles", "backup_codes"])
async def test_unread_relationships_refuse_to_lazy_load(seeded, name):
    maker, _ = seeded

    async with maker() as session:
        user = (await session.execute(
            select(User).where(User.id == 1)
        )).scalars().first()

        with pytest.raises(InvalidRequestError): len(getattr(user, name))


async def test_hashing_does_not_block_the_loop():
    service = HashService(2, 8192, 1, threads=2)

    digest = await service.ahash("Sicher123!")
    assert await service.averify(digest, "Sicher123!")
    assert await service.averify(digest, "falsch") is False


def test_password_policy_reports_every_violation():
    policy = PasswordPolicy(8, { "lower": 1, "upper": 1, "digits": 1, "special": 1 })

    with pytest.raises(ValueError) as info: policy.validate("abc")

    assert set(info.value.errors) == {
        "MIN_LENGTH_8", "MIN_UPPER_1", "MIN_DIGITS_1", "MIN_SPECIAL_1"
    }


def test_password_policy_accepts_a_valid_password():
    policy = PasswordPolicy(8, { "lower": 1, "upper": 1, "digits": 1, "special": 1 })
    assert policy.validate("Sicher123!") == "Sicher123!"


async def test_a_non_numeric_bearer_subject_is_not_a_server_error(monkeypatch):
    from types import SimpleNamespace
    import webfluid.core.ext as ext
    from webfluid.extensions.security.services.user.gating.bearer import resolve

    async def adecode(_): return { "sub": "a-uuid", "permissions": ["read"] }

    monkeypatch.setattr(resolve, "EXT_JWT", True)
    monkeypatch.setattr(
        ext, "jwt", SimpleNamespace(adecode=adecode), raising=False
    )
    request = SimpleNamespace(headers={ "Authorization": "Bearer token" })

    assert [r async for r in resolve.resolve_bearer(request, "read")] == [(None, False)]


async def test_a_numeric_bearer_subject_still_resolves(monkeypatch, seeded):
    from types import SimpleNamespace
    import webfluid.core.ext as ext
    from webfluid.extensions.security.services.user.gating.bearer import resolve

    maker, _ = seeded
    async def adecode(_): return { "sub": "1", "permissions": ["read"] }

    monkeypatch.setattr(resolve, "EXT_JWT", True)
    monkeypatch.setattr(
        ext, "jwt", SimpleNamespace(adecode=adecode), raising=False
    )
    monkeypatch.setattr(db, "async_executor", lambda **_: AsyncExecutor(maker()))
    request = SimpleNamespace(headers={ "Authorization": "Bearer token" })

    resolved = [r async for r in resolve.resolve_bearer(request, "read")]

    assert len(resolved) == 1
    assert (resolved[0][0].id, resolved[0][1]) == (1, True)


def test_an_unknown_kid_is_an_invalid_token(monkeypatch):
    from types import SimpleNamespace
    import jwt as pyjwt
    import webfluid.core.ext as ext
    from webfluid.extensions.jwt.decode import Decoder

    token = pyjwt.encode({ "sub": "1" }, "x" * 32, headers={ "kid": "gone" })
    monkeypatch.setattr(
        ext, "cache", SimpleNamespace(get=lambda _: None), raising=False
    )

    decoder = Decoder(SimpleNamespace(
        algorithm="HS256", issuer="tests", audience=lambda name: name
    ))

    with pytest.raises(pyjwt.InvalidTokenError): decoder.decode(token)
