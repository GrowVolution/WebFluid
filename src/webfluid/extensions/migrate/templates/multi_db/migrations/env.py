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


def get_engine(bind_key="default"):
    return db.get_bind(bind_key).async_engine


def get_engine_url(bind_key="default"):
    engine = get_engine(bind_key)
    return str(engine.url).replace("%", "%%")


config.set_main_option("sqlalchemy.url", get_engine_url("default"))

bind_names = [b for b in db.bind_keys if b != "default"]

for bind in bind_names:
    context.config.set_section_option(
        bind,
        "sqlalchemy.url",
        get_engine_url(bind)
    )


def get_metadata(bind_key):
    return db.get_bind(bind_key).metadata


def is_downgrade() -> bool:
    opts = getattr(config, "cmd_opts", None)
    cmd = getattr(opts, "cmd", None) if opts else None
    return bool(cmd) and getattr(cmd[0], "__name__", "") == "downgrade"


def run_migrations_offline():

    engines = {
        "default": {
            "url": config.get_main_option("sqlalchemy.url")
        }
    }

    for name in bind_names:
        engines[name] = {
            "url": context.config.get_section_option(name, "sqlalchemy.url")
        }

    names = list(engines)
    if is_downgrade(): names = list(reversed(names))

    for name in names:
        rec = engines[name]

        logger.info(f"Migrating database {name}")

        context.configure(
            url=rec["url"],
            target_metadata=get_metadata(name),
            literal_binds=True,
            compare_type=True,
            render_as_batch=rec["url"].startswith("sqlite"),
        )

        with context.begin_transaction():
            context.run_migrations(engine_name=name)


def do_run_migrations(connection, name):

    def process_revision_directives(context_, revision, directives):
        if not directives: return
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if all(op.is_empty() for op in script.upgrade_ops_list):
                logger.info("No schema changes detected.")

    context.configure(
        connection=connection,
        target_metadata=get_metadata(name),
        upgrade_token="%s_upgrades" % name,
        downgrade_token="%s_downgrades" % name,
        compare_type=True,
        process_revision_directives=process_revision_directives,
        render_as_batch=connection.dialect.name == "sqlite",
    )

    with context.begin_transaction():
        context.run_migrations(engine_name=name)


async def run_migrations_online():

    engines = {
        "default": get_engine("default")
    }

    for name in bind_names:
        engines[name] = get_engine(name)

    names = list(engines)
    if is_downgrade(): names = list(reversed(names))

    for name in names:
        engine = engines[name]

        logger.info(f"Migrating database {name}")

        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations, name)


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())