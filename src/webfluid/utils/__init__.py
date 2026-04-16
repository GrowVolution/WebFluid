from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid.utils.framework import *

__all__ = [
    "enabled", "random_code", "safe_string", "camel_to_snake", "get_root_path", "required_arg_count",
    "is_async_function", "async_result", "safe_execute", "run_in_executor", "check_priority",
    "build_sorted_tuple", "try_import", "check_required_version",
    "get_proxy", "get_websocket_proxy", "add_proxy", "close_proxy_client",

    "additive", "logging"
]


def __getattr__(name):
    if name in {
        "enabled", "random_code", "safe_string", "camel_to_snake", "get_root_path", "required_arg_count",
        "is_async_function", "async_result", "safe_execute", "run_in_executor", "check_priority",
        "build_sorted_tuple", "try_import", "check_required_version",
        "get_proxy", "get_websocket_proxy", "add_proxy", "close_proxy_client"
    }:
        from . import framework
        return getattr(framework, name)

    raise AttributeError(name)
