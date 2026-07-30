from sqlalchemy import MetaData, inspect
from sqlalchemy.orm import DeclarativeBase, declared_attr

from webfluid.utils.core import camel_to_snake
from webfluid.exceptions import FrameworkException


class Model(DeclarativeBase):
    __bind_set__ = False
    __metadata__ = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        key = cls.__dict__.get("__bind_key__")
        if key and not cls.__bind_set__:
            cls.set_bind(key)

    def __hash__(self):
        state = inspect(self)
        return hash(state.identity)

    @declared_attr
    def __tablename__(cls):
        tablename = cls.__dict__.get("__tablename__")
        if isinstance(tablename, str):
            return tablename
        return camel_to_snake(cls.__name__)

    @classmethod
    def metadata_for(cls, key):
        if key == "default": return Model.metadata
        md = Model.__metadata__.get(key)
        if md is None:
            md = MetaData()
            Model.__metadata__[key] = md
        return md

    @classmethod
    def set_bind(cls, key):
        if cls.__bind_set__:
            raise FrameworkException(
                f"DB bind has already been set for {cls.__name__}!"
            )
        cls.__bind_key__ = key
        cls.__bind_set__ = True

        table = getattr(cls, "__table__", None)
        target = cls.metadata_for(key)
        if table is None or table.metadata is target: return

        from .utils import update_metadata
        update_metadata(table, target)
