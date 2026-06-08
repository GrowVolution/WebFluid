from sqlalchemy import Table, Column, Integer, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, relationship, mapped_column
from datetime import datetime
from typing import Optional

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
    email: Mapped[Optional[str]]
    pending_email: Mapped[Optional[str]]
    email_verified: Mapped[bool] = mapped_column(default=False)
    psw_hash: Mapped[Optional[str]]
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )

    identities: Mapped[list[Identity]] = relationship(
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles,
        back_populates="users",
        lazy="selectin"
    )

    def __init__(self, username: str, email: Optional[str],
                 psw_hash: Optional[str] = None):
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
        lazy="selectin"
    )

    def __init__(self, user_id: int, sub: str, provider: str):
        self.user_id = user_id
        self.sub = sub
        self.provider = provider


class Role(db.Model):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    is_admin: Mapped[bool] = mapped_column(default=False)

    users: Mapped[list[User]] = relationship(
        secondary=user_roles,
        back_populates="roles",
        lazy="selectin"
    )
    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin"
    )

    def __init__(self, name: str):
        self.name = name
        self.users = []
        self.permissions = []


class Permission(db.Model):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)

    roles: Mapped[list[Role]] = relationship(
        secondary=role_permissions,
        back_populates="permissions",
        lazy="selectin"
    )

    def __init__(self, name: str):
        self.name = name
        self.roles = []
