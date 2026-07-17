from .default import DefaultConfig
from .main import ConfigMeta, config_map
from webfluid.utils.core import build_sorted_tuple


def build_config():
    cls = DefaultConfig
    default_conf = ConfigMeta(cls.__name__, cls.__bases__, dict(cls.__dict__))

    bases = tuple()
    for configs in build_sorted_tuple(config_map):
        bases += tuple(configs)

    return ConfigMeta(
        "Config",
        bases + (default_conf,),
        {}
    )
