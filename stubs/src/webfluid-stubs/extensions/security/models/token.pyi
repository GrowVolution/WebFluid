from sqlalchemy.orm import Mapped
from datetime import datetime

from webfluid.extensions.sqlalchemy.model import Model


class ExpiredToken(Model):
    __tablename__: str
    id: Mapped[int]
    token: Mapped[str]
    created_at: Mapped[datetime]
    def __init__(self, token: str) -> None: ...
