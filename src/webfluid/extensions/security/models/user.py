from sqlalchemy import Table, Column, Integer, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, relationship, mapped_column
from datetime import datetime

from webfluid.core.ext import db


user_roles = Table(
    "user_roles", db.Model.metadata,

    Column("user_id", Integer,
           ForeignKey("users.id", ondelete="CASCADE")),

    Column("role_id", Integer,
           ForeignKey("roles.id", ondelete="CASCADE"))
)

role_permissions = Table(
    "role_permissions", db.Model.metadata,

    Column("role_id", Integer,
           ForeignKey("roles.id", ondelete="CASCADE")),

    Column("permission_id", Integer,
           ForeignKey("permissions.id", ondelete="CASCADE"))
)


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str | None]
    pending_email: Mapped[str | None]
    email_verified: Mapped[bool] = mapped_column(default=False)
    psw_hash: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )

    identities: Mapped[list[Identity]] = relationship(
        back_populates="user",
        lazy="raise_on_sql",
        cascade="all, delete-orphan"
    )
    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles,
        back_populates="users",
        lazy="raise_on_sql"
    )

    totp_secret: Mapped[TOTPSecret | None] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
        uselist=False
    )
    webauthn_credentials: Mapped[list[WebAuthnCredential]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    backup_codes: Mapped[list[BackupCode]] = relationship(
        back_populates="user",
        lazy="raise_on_sql",
        cascade="all, delete-orphan"
    )

    def __init__(self, username, email, psw_hash=None):
        self.username = username
        self.email = email
        self.psw_hash = psw_hash
        self.identities = []
        self.roles = []


class Identity(db.Model):
    __tablename__ = "identities"
    __table_args__ = (UniqueConstraint("sub", "provider"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id, ondelete="CASCADE"))

    sub: Mapped[str]
    provider: Mapped[str]

    user: Mapped[User] = relationship(
        back_populates="identities",
        lazy="raise_on_sql"
    )

    def __init__(self, user_id, sub, provider):
        self.user_id = user_id
        self.sub = sub
        self.provider = provider


class TOTPSecret(db.Model):
    __tablename__ = "totp_secrets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(User.id, ondelete="CASCADE"), unique=True
    )

    secret: Mapped[str]
    confirmed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )

    user: Mapped[User] = relationship(
        back_populates="totp_secret",
        lazy="raise_on_sql"
    )

    def __init__(self, user_id, secret):
        self.user_id = user_id
        self.secret = secret


class WebAuthnCredential(db.Model):
    __tablename__ = "webauthn_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id, ondelete="CASCADE"))

    credential_id: Mapped[str] = mapped_column(unique=True)
    public_key: Mapped[str]
    sign_count: Mapped[int] = mapped_column(default=0)
    transports: Mapped[str | None]
    name: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )

    user: Mapped[User] = relationship(
        back_populates="webauthn_credentials",
        lazy="raise_on_sql"
    )

    def __init__(self, user_id, credential_id, public_key,
                 sign_count=0, transports=None, name=None):
        self.user_id = user_id
        self.credential_id = credential_id
        self.public_key = public_key
        self.sign_count = sign_count
        self.transports = transports
        self.name = name


class BackupCode(db.Model):
    __tablename__ = "backup_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id, ondelete="CASCADE"))

    code_hash: Mapped[str]
    used: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )

    user: Mapped[User] = relationship(
        back_populates="backup_codes",
        lazy="raise_on_sql"
    )

    def __init__(self, user_id, code_hash):
        self.user_id = user_id
        self.code_hash = code_hash


class Role(db.Model):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    requires_2fa: Mapped[bool] = mapped_column(default=False)

    users: Mapped[list[User]] = relationship(
        secondary=user_roles,
        back_populates="roles",
        lazy="raise_on_sql"
    )
    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions,
        back_populates="roles",
        lazy="raise_on_sql"
    )

    def __init__(self, name, require_2fa=False):
        self.name = name
        self.requires_2fa = require_2fa
        self.users = []
        self.permissions = []


class Permission(db.Model):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)

    roles: Mapped[list[Role]] = relationship(
        secondary=role_permissions,
        back_populates="permissions",
        lazy="raise_on_sql"
    )

    def __init__(self, name):
        self.name = name
        self.roles = []
