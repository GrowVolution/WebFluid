from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, UTC
from uuid import uuid4
import secrets


async def _rotate_secret(config):
    from webfluid.core.ext import cache

    current_key = uuid4().hex
    await cache.aset(
        f"jwt:{current_key}",
        secrets.token_hex(config.secret_length),
        365 * 24 * 60 * 60
    )
    await cache.aset(
        "jwt:current", current_key,
        (config.rotary_interval + 1) * 24 * 60 * 60
    )


def add_job(fluid, config):
    from webfluid.core.ext import scheduler

    rotate_secret = lambda: _rotate_secret(config)
    fluid.startup_hook(rotate_secret)
    scheduler.add_job(
        rotate_secret,
        IntervalTrigger(
            days=config.rotary_interval,
            start_date=datetime.now(UTC)
        )
    )
