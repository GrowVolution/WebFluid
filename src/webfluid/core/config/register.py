from .main import ConfigMeta, config_map
from webfluid.utils.core import check_priority


def register_config(priority=1):
    check_priority(priority)

    def decorator(cls):
        if not priority in config_map:
            config_map[priority] = []

        if not isinstance(type(cls), ConfigMeta):
            cls = ConfigMeta(cls.__name__, cls.__bases__, dict(cls.__dict__))

        config_map[priority].append(cls)
        return cls

    return decorator
