
__all__ = [
    "enabled", "random_code", "safe_string", "camel_to_snake", "final_version", "get_root_path",
    "parse_config", "required_arg_count", "is_async_function", "async_result", "safe_execute",
    "run_in_executor", "check_priority", "build_sorted_tuple", "try_import", "check_required_version",
    "get_proxy", "get_websocket_proxy", "add_proxy", "close_proxy_client",

    "additives", "ocean", "countries", "logging"
]


def __getattr__(name):
    if name in {
        "enabled", "random_code", "safe_string", "camel_to_snake", "final_version", "get_root_path",
        "parse_config", "required_arg_count", "is_async_function", "async_result", "safe_execute",
        "run_in_executor", "check_priority", "build_sorted_tuple", "try_import", "check_required_version",
        "get_proxy", "get_websocket_proxy", "add_proxy", "close_proxy_client"
    }:
        from . import core
        return getattr(core, name)

    raise AttributeError(name)
