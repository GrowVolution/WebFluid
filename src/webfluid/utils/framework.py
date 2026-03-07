from pathlib import Path
from typing import TYPE_CHECKING, Callable, Any
import os, inspect, random, string, logging, re, asyncio, sys, importlib

if TYPE_CHECKING:
    from webfluid import AdditiveVersion


def enabled(key: str) -> bool:
    return os.getenv(key, "false").lower() in ["true", "1", "yes"]


def random_code(length: int = 6) -> str:
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))


def safe_string(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text)


def camel_to_snake(text: str) -> str:
    return re.sub(r'(?<!^)(?=[A-Z])', '_', text).lower()


def sanitize_text(value: str) -> str:
    return value.encode("utf-8", "ignore").decode("utf-8")


def get_root_path(import_name: str) -> str:
    mod = sys.modules.get(import_name)

    if mod and getattr(mod, "__file__", None):
        return str(Path(mod.__file__).resolve().parent)

    try:
        spec = importlib.util.find_spec(import_name)
    except (ImportError, ValueError):
        spec = None

    loader = getattr(spec, "loader", None)

    if loader is None:
        return str(Path.cwd())

    if hasattr(loader, "get_filename"):
        filepath = loader.get_filename(import_name)
    else:
        __import__(import_name)
        mod = sys.modules.get(import_name)
        filepath = getattr(mod, "__file__", None)

        if filepath is None:
            raise RuntimeError(
                f"No root path can be found for the provided module {import_name!r}."
            )

    return str(Path(filepath).resolve().parent)


def required_arg_count(fn: Callable) -> int:
    sig = inspect.signature(fn)

    return sum(
        1
        for p in sig.parameters.values()
        if p.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
        and p.default is inspect._empty
    )


def is_async_function(fn: Callable) -> bool:
    return inspect.iscoroutinefunction(fn)


async def async_result(result: Any) -> Any:
    if inspect.isawaitable(result):
        return await result
    return result


async def safe_execute(
        fn: Callable, exception_class: type[Exception],
        *args, **kwargs
) -> Any:
    try: return await async_result(fn(*args, **kwargs))
    except Exception as e: raise exception_class(e)


async def run_in_executor(fn: Callable, *args, executor=None):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, fn, *args)


def decorate(decorator: Callable, handler: Callable | type) -> Callable | type:
    if handler is None: return decorator
    return decorator(handler)


def check_priority(priority: int):
    if priority not in range(1, 11):
        raise ValueError("Priority must be between 1 and 10.")


def build_sorted_tuple(data: dict[int, Any], defaults: tuple = None) -> tuple:
    sorted_data = dict(sorted(data.items(), reverse=True)).values()
    result = tuple(sorted_data)
    if defaults is not None:
        result += defaults
    return result


def check_required_version(requirement: str, version_type: str = "wf", additive_version: "AdditiveVersion | str" = None) -> bool:
    version_type = version_type.lower()
    if version_type not in ["wf", "additive"]:
        raise ValueError("Invalid version type.")

    if version_type == "additive" and additive_version is None:
        raise RuntimeError("Cannot check with unknown additive version.")

    from webfluid import FluidVersion, AdditiveVersion, version
    ver_cls = FluidVersion if version_type == "wf" else AdditiveVersion

    if requirement != "*":
        for candidate in (">=", "<=", "==", ">", "<"):
            if requirement.startswith(candidate):
                op = candidate
                ver = requirement[len(candidate):].strip()
                break
        else:
            raise ValueError(f"Invalid version operator in requirement '{requirement}'.")
    else:
        return True

    if version_type == "additive":
        current = additive_version if isinstance(additive_version, ver_cls) \
            else ver_cls(*map(int, additive_version.split(".")))
    else:
        current = version()

    try:
        target = ver_cls(*map(int, ver.split(".")))
    except ValueError:
        raise ValueError("Invalid requirement string.")

    return {
        ">":  current > target,
        ">=": current >= target,
        "<":  current < target,
        "<=": current <= target,
        "==": current == target,
    }.get(op, False)


def disable_uvicorn_logging():
    logging.getLogger("uvicorn").disabled = True
    logging.getLogger("uvicorn.error").disabled = True
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("uvicorn.asgi").disabled = True
