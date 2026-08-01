
__all__ = [
    "enabled", "random_code", "safe_string",
    "camel_to_snake", "get_root_path", "parse_config",
    "check_priority", "build_sorted_tuple", "try_import",

    "required_arg_count", "async_result",
    "safe_execute", "run_in_executor",

    "Version", "check_required_version",

    "get_proxy", "get_websocket_proxy",
    "add_proxy", "close_proxy_client"
]


def __getattr__(name):
    if name in {
        "enabled", "random_code", "safe_string",
        "camel_to_snake", "get_root_path", "parse_config",
        "check_priority", "build_sorted_tuple", "try_import"
    }:
        from . import main
        return getattr(main, name)

    if name in {
        "required_arg_count", "async_result",
        "safe_execute", "run_in_executor"
    }:
        from . import func
        return getattr(func, name)

    if name in {"Version", "check_required_version"}:
        from . import versioning
        return getattr(versioning, name)

    if name in {
        "get_proxy", "get_websocket_proxy",
        "add_proxy", "close_proxy_client"
    }:
        from . import proxy
        return getattr(proxy, name)

    raise AttributeError(name)


def __dir__(): return sorted(__all__)
