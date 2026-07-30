from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class Model(DeclarativeBase):
    __bind_set__: bool
    __metadata__: dict[str, MetaData]
    def __init_subclass__(cls, **kwargs: Any) -> None: ...
    def __hash__(self) -> int: ...
    @classmethod
    def metadata_for(cls, key: str) -> MetaData: ...
    @classmethod
    def set_bind(cls, key: str) -> None: ...
