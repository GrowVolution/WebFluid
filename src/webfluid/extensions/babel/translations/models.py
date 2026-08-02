from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UniqueConstraint, ForeignKey
from typing import Optional

from webfluid.core.ext import db


class I18nKey(db.Model):
    __tablename__ = "i18n_keys"
    __table_args__ = (UniqueConstraint("key", "domain"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str]
    domain: Mapped[str]
    cached: Mapped[bool]

    messages: Mapped[list[I18nMessage]] = relationship(
        back_populates="key",
        lazy="raise_on_sql"
    )

    def __init__(self, key, domain, cached=True):
        self.key = key
        self.domain = domain
        self.cached = cached


class I18nMessage(db.Model):
    __tablename__ = "i18n"
    __table_args__ = (UniqueConstraint("locale", "kid", "pf", "ctx"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kid: Mapped[int] = mapped_column(ForeignKey("i18n_keys.id"))

    locale: Mapped[str]
    pf: Mapped[str]
    text: Mapped[str]
    ctx: Mapped[Optional[str]]

    key: Mapped[I18nKey] = relationship(
        back_populates="messages",
        lazy="raise_on_sql"
    )

    def __init__(self, kid, locale, text, pf="one", ctx=None):
        self.kid = kid
        self.locale = locale
        self.pf = pf
        self.text = text
        if ctx is not None: self.ctx = ctx
