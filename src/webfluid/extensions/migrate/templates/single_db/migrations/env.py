from alembic import context
from logging.config import fileConfig
import asyncio, logging

from webfluid.core.context import FluidContext
from webfluid.extensions.sqlalchemy import SQLAlchemy
from webfluid.utils import try_import, enabled
from webfluid.utils.additives import installed_additives

config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")


def get_fluid():
    import main
    if hasattr(main, "prepare_fluid"):
        app = main.prepare_fluid()
    elif hasattr(main, "fluid"):
        app = main.fluid
    else: raise ValueError(
        "Missing fluid instance or prepare_fluid function in main.py"
    )

    with FluidContext(app):
        try_import("fluid.models")
        for additive in installed_additives(app.project_root / "additives"):
            a, _, p = additive
            if not enabled(a): continue
            try_import(f"additives.{p}.models")

    return app

fluid = get_fluid()


db = SQLAlchemy.get_instance()
target_metadata = db.Model.metadata


def get_engine():
    return db.get_bind("default").async_engine


def get_engine_url():
    engine = get_engine()
    return str(engine.url).replace("%", "%%")


config.set_main_option("sqlalchemy.url", get_engine_url())


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):

    def process_revision_directives(context_, revision, directives):
        if not directives: return
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                logger.info("No schema changes detected.")

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        process_revision_directives=process_revision_directives,
        render_as_batch=connection.dialect.name == "sqlite",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():

    connectable = get_engine()

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())