from .main import config_map
from webfluid.utils.core import check_priority


def register_config(priority=1):
    check_priority(priority)

    def decorator(cls):
        if priority not in config_map:
            config_map[priority] = []

        config_map[priority].append(cls)
        return cls

    return decorator
