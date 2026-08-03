from sqlalchemy.orm import DeclarativeBase


def _with_driver(uri, scheme, driver):
    return f"{scheme}+{driver}{uri[len(scheme):]}"


def database_uris(uri):
    if "+" in uri.split("://")[0]:
        raise ValueError(f"Invalid database URI '{uri}': Please do not define drivers.")

    if uri.startswith("sqlite:"):
        sync_uri = uri
        async_uri = _with_driver(uri, "sqlite", "aiosqlite")
    elif uri.startswith("postgresql:"):
        sync_uri = _with_driver(uri, "postgresql", "psycopg")
        async_uri = sync_uri
    elif uri.startswith("mysql:"):
        sync_uri = _with_driver(uri, "mysql", "pymysql")
        async_uri = _with_driver(uri, "mysql", "aiomysql")
    else:
        raise ValueError(f"Invalid database URI '{uri}': Unsupported database type.")

    return sync_uri, async_uri


def update_metadata(table, target_md=None, target_bind=None, target_model=None):
    if target_md: md = target_md

    elif target_bind:
        from .sqlalchemy import SQLAlchemy
        db = SQLAlchemy.get_instance()
        bind = db.get_bind(target_bind)
        md = bind.metadata

    elif target_model:
        if not issubclass(target_model, DeclarativeBase):
            raise ValueError(f"Invalid model type '{target_model}'.")
        md = getattr(target_model.__table__, "metadata", target_model.metadata)

    else: raise ValueError("Failed to resolve metadata.")

    table.metadata._remove_table(table.name, table.schema)
    table.metadata = md
    md._add_table(table.name, table.schema, table)
