from alembic import context
from logging.config import fileConfig
import asyncio, logging

from webfluid.core.context import FluidContext
from webfluid.extensions.sqlalchemy import SQLAlchemy
from webfluid.utils import try_import

config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")


def get_fluid():
    from main import create_app
    app = create_app()

    with FluidContext(app):
        try_import("fluid.models")
        for pkg in (app.app_root / "additives").iterdir():
            if not pkg.is_dir(): continue
            try_import(f"additives.{pkg.name}.models")

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