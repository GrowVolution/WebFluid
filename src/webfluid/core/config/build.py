from .default import DefaultConfig
from .main import config_map
from webfluid.utils.core import build_sorted_tuple


def _values(cls):
    values = {}
    for base in reversed(cls.__mro__):
        for key, value in vars(base).items():
            if key.isupper(): values[key] = value
    return values


def build_config():
    config = _values(DefaultConfig)

    for configs in build_sorted_tuple(config_map):
        for cls in configs: config.update(_values(cls))

    return config
