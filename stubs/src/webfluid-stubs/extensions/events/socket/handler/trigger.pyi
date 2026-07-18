from typing import Any

from webfluid.extensions.events.events import Events

def trigger(events: Events, msg: dict[str, Any], res: dict[str, Any]) -> dict[str, Any]: ...
