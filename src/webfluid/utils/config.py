from importlib import import_module
from typing import Callable, TYPE_CHECKING

from webfluid.core.api.config import DefaultConfig as apiDefaultConfig
from webfluid.core.app.config import DefaultConfig as appDefaultConfig
from webfluid.additives import installed_additives
from webfluid.utils import enabled, check_priority, build_sorted_tuple

if TYPE_CHECKING:
    from webfluid import Fluid

_api_config_map: dict[int, list[type]] = {}
_app_config_map: dict[int, list[type]] = {}

class ConfigMeta(type): pass


def _build(config_map: dict, default_config: type) -> ConfigMeta:
    cls = default_config
    default_conf = ConfigMeta(cls.__name__, cls.__bases__, dict(cls.__dict__))

    bases = tuple()
    for configs in build_sorted_tuple(config_map):
        bases += tuple(configs)

    return ConfigMeta(
        "Config",
        bases + (default_conf,),
        {}
    )


def init_configs(app: "Fluid"):
    additives = app.app_root / "additives"
    if not additives.exists() or not additives.is_dir(): return
    for additive_info in installed_additives(additives):
        m, _, p = additive_info
        if not enabled(m): continue
        try: import_module(f"additives.{p}.config")
        except ModuleNotFoundError: pass


def api_config(priority: int = 1) -> Callable:
    check_priority(priority)

    def decorator(cls):
        if not priority in _api_config_map:
            _api_config_map[priority] = []

        if not isinstance(type(cls), ConfigMeta):
            cls = ConfigMeta(cls.__name__, cls.__bases__, dict(cls.__dict__))

        _api_config_map[priority].append(cls)
        return cls

    return decorator


def app_config(priority: int = 1) -> Callable:
    check_priority(priority)

    def decorator(cls):
        if not priority in _app_config_map:
            _app_config_map[priority] = []

        if not isinstance(type(cls), ConfigMeta):
            cls = ConfigMeta(cls.__name__, cls.__bases__, dict(cls.__dict__))

        _app_config_map[priority].append(cls)
        return cls

    return decorator


def build_api_config() -> ConfigMeta:
    return _build(_api_config_map, apiDefaultConfig)

def build_app_config() -> ConfigMeta:
    return _build(_app_config_map, appDefaultConfig)
