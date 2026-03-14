from alembic import context
from logging.config import fileConfig
import asyncio, logging

from webfluid.core.ext import db

# Alembic config
config = context.config

fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

# -----------------------------------------------------
# Load Fluid app
# -----------------------------------------------------

def get_fluid():
    from main import create_app
    return create_app()

fluid = get_fluid()

# SQLAlchemy metadata
target_metadata = db.Model.metadata


# -----------------------------------------------------
# Engine resolution
# -----------------------------------------------------

def get_engine():
    # default bind
    return db.binds["default"].async_engine


def get_engine_url():
    engine = get_engine()
    return str(engine.url).replace("%", "%%")


config.set_main_option("sqlalchemy.url", get_engine_url())


# -----------------------------------------------------
# Offline migrations
# -----------------------------------------------------

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


# -----------------------------------------------------
# Online migrations
# -----------------------------------------------------

def do_run_migrations(connection):

    def process_revision_directives(context_, revision, directives):
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
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


# -----------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())