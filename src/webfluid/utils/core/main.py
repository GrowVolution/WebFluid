from pathlib import Path
from importlib import import_module
import os, random, string, re, sys, importlib


def enabled(key):
    return os.getenv(key, "").lower() in ["true", "1", "yes"]


def random_code(length=6):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))


def safe_string(text):
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text)


def camel_to_snake(text):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', text).lower()


def get_root_path(import_name):
    mod = sys.modules.get(import_name)

    if mod and getattr(mod, "__file__", None):
        return str(Path(mod.__file__).resolve().parent)

    try: spec = importlib.util.find_spec(import_name)
    except (ImportError, ValueError): spec = None

    loader = getattr(spec, "loader", None)
    if loader is None: return str(Path.cwd())

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


def parse_config(key, value):
    if key.endswith("_FILE"):
        file = Path(value).expanduser().resolve()
        if not file.exists(): return key, value
        return key.removesuffix("_FILE"), file.read_text(encoding="utf-8")
    return key, value


def check_priority(priority):
    if priority not in range(1, 11):
        raise ValueError("Priority must be between 1 and 10.")


def build_sorted_tuple(data, defaults=None):
    sorted_data = dict(sorted(data.items(), reverse=True)).values()
    result = tuple(sorted_data)
    if defaults is not None:
        result += defaults
    return result


def try_import(name):
    try: return import_module(name)
    except ModuleNotFoundError as e:
        if e.name != name: raise
