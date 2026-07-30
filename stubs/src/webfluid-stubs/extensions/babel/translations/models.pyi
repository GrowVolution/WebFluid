from typing import Optional

from sqlalchemy.orm import Mapped


class I18nKey:
    id: Mapped[int]
    key: Mapped[str]
    domain: Mapped[str]
    cached: Mapped[bool]
    messages: Mapped[list[I18nMessage]]
    def __init__(self, key: str, domain: str, cached: bool = True) -> None: ...


class I18nMessage:
    id: Mapped[int]
    kid: Mapped[int]
    locale: Mapped[str]
    pf: Mapped[str]
    text: Mapped[str]
    ctx: Mapped[Optional[str]]
    key: Mapped[I18nKey]
    def __init__(
        self, kid: int, locale: str, text: str, pf: str = "one", ctx: str | None = None
    ) -> None: ...
