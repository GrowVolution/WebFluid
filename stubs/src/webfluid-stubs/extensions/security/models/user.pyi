from sqlalchemy import Table
from sqlalchemy.orm import Mapped
from datetime import datetime

from webfluid.extensions.sqlalchemy.model import Model

user_roles: Table
role_permissions: Table


class User(Model):
    __tablename__: str
    id: Mapped[int]
    username: Mapped[str]
    email: Mapped[str | None]
    pending_email: Mapped[str | None]
    email_verified: Mapped[bool]
    psw_hash: Mapped[str | None]
    created_at: Mapped[datetime]
    identities: Mapped[list[Identity]]
    roles: Mapped[list[Role]]
    totp_secret: Mapped[TOTPSecret | None]
    webauthn_credentials: Mapped[list[WebAuthnCredential]]
    backup_codes: Mapped[list[BackupCode]]
    def __init__(self, username: str, email: str | None, psw_hash: str | None = None) -> None: ...


class Identity(Model):
    __tablename__: str
    id: Mapped[int]
    user_id: Mapped[int]
    sub: Mapped[str]
    provider: Mapped[str]
    user: Mapped[User]
    def __init__(self, user_id: int, sub: str, provider: str) -> None: ...


class TOTPSecret(Model):
    __tablename__: str
    id: Mapped[int]
    user_id: Mapped[int]
    secret: Mapped[str]
    confirmed: Mapped[bool]
    created_at: Mapped[datetime]
    user: Mapped[User]
    def __init__(self, user_id: int, secret: str) -> None: ...


class WebAuthnCredential(Model):
    __tablename__: str
    id: Mapped[int]
    user_id: Mapped[int]
    credential_id: Mapped[str]
    public_key: Mapped[str]
    sign_count: Mapped[int]
    transports: Mapped[str | None]
    name: Mapped[str | None]
    created_at: Mapped[datetime]
    user: Mapped[User]
    def __init__(
        self, user_id: int, credential_id: str, public_key: str,
        sign_count: int = 0, transports: str | None = None, name: str | None = None,
    ) -> None: ...


class BackupCode(Model):
    __tablename__: str
    id: Mapped[int]
    user_id: Mapped[int]
    code_hash: Mapped[str]
    used: Mapped[bool]
    created_at: Mapped[datetime]
    user: Mapped[User]
    def __init__(self, user_id: int, code_hash: str) -> None: ...


class Role(Model):
    __tablename__: str
    id: Mapped[int]
    name: Mapped[str]
    is_admin: Mapped[bool]
    requires_2fa: Mapped[bool]
    users: Mapped[list[User]]
    permissions: Mapped[list[Permission]]
    def __init__(self, name: str, require_2fa: bool = False) -> None: ...


class Permission(Model):
    __tablename__: str
    id: Mapped[int]
    name: Mapped[str]
    roles: Mapped[list[Role]]
    def __init__(self, name: str) -> None: ...
