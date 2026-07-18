from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, UTC
from uuid import uuid4
import secrets


async def _rotate_secret(jwt_manager):
    from webfluid.core.ext import cache
    current_key = uuid4().hex
    await cache.aset(
        f"jwt:{current_key}",
        secrets.token_hex(jwt_manager._secret_length),
        365 * 24 * 60 * 60
    )
    timeout = jwt_manager._secret_rotary_interval + 1
    await cache.aset(
        "jwt:current", current_key,
        timeout * 24 * 60 * 60
    )


def add_job(fluid, jwt_manager):
    from webfluid.core.ext import scheduler
    rotate_secret = lambda: _rotate_secret(jwt_manager)
    fluid.startup_hook(rotate_secret)
    scheduler.add_job(
        rotate_secret,
        IntervalTrigger(
            days=jwt_manager._secret_rotary_interval,
            start_date=datetime.now(UTC)
        )
    )
