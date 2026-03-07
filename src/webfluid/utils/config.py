from importlib import import_module
from typing import TYPE_CHECKING, Callable

from webfluid.core.config import DefaultConfig
from webfluid.additives import installed_additives
from webfluid.utils import enabled, check_priority, build_sorted_tuple

if TYPE_CHECKING:
    from webfluid import Fluid

_config_map: dict[int, list[type]] = {}

class ConfigMeta(type): pass


def init_configs(fluid: "Fluid"):
    additives = fluid.app_root / "additives"
    if not additives.exists() or not additives.is_dir(): return
    for additive in installed_additives(additives, True):
        a, _, p = additive
        if not enabled(a): continue
        try: import_module(f"additives.{p}.config")
        except ModuleNotFoundError: pass


def register_config(priority: int = 1) -> Callable:
    check_priority(priority)

    def decorator(cls):
        if not priority in _config_map:
            _config_map[priority] = []

        if not isinstance(type(cls), ConfigMeta):
            cls = ConfigMeta(cls.__name__, cls.__bases__, dict(cls.__dict__))

        _config_map[priority].append(cls)
        return cls

    return decorator


def build_config() -> ConfigMeta:
    cls = DefaultConfig
    default_conf = ConfigMeta(cls.__name__, cls.__bases__, dict(cls.__dict__))

    bases = tuple()
    for configs in build_sorted_tuple(_config_map):
        bases += tuple(configs)

    return ConfigMeta(
        "Config",
        bases + (default_conf,),
        {}
    )
