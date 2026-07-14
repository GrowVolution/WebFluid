from fastapi import Request, Response, WebSocket
from starlette.websockets import WebSocketDisconnect
from pathlib import Path
from importlib import import_module
import os, inspect, random, string, re, asyncio, \
    sys, importlib, httpx, websockets

_stage_map = {
    "a": 0,
    "b": 1,
    "rc": 2
}

_proxy_client = httpx.AsyncClient()


def enabled(key):
    return os.getenv(key, "").lower() in ["true", "1", "yes"]


def random_code(length=6):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))


def safe_string(text):
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text)


def camel_to_snake(text):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', text).lower()


def final_version(v_str):
    if "a" in v_str:
        stage = "a"
        v, build = map(int, v_str.split("a"))
    elif "b" in v_str:
        stage = "b"
        v, build = map(int, v_str.split("b"))
    elif "rc" in v_str:
        stage = "rc"
        v, build = map(int, v_str.split("rc"))
    else:
        stage = ""
        v, build = int(v_str), 0

    return v, stage, build


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


def required_arg_count(fn):
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


def is_async_function(fn):
    return inspect.iscoroutinefunction(fn)


async def async_result(result):
    if asyncio.iscoroutine(result):
        return await result
    return result


async def safe_execute(fn, reraise, *args, **kwargs):
    try: return await async_result(fn(*args, **kwargs))
    except Exception as e:
        if reraise: raise
        else:
            from .logging import factory as log_factory
            log_factory.exception(e)
    return None


async def run_in_executor(fn, *args, executor=None):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, fn, *args)


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


def check_required_version(requirement, version_type="wf", additive_version=None):
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
            else ver_cls(*additive_version.split("."))
    else:
        current = version()

    try: target = ver_cls(*ver.split("."))
    except ValueError:
        raise ValueError("Invalid requirement string.")

    current_stage = _stage_map.get(current.stage, 3)
    target_stage = _stage_map.get(target.stage, 3)

    return {
        ">":  current > target and (current_stage > target_stage or current.build > target.build),
        ">=": current >= target and (current_stage >= target_stage or current.build >= target.build),
        "<":  current < target and (current_stage < target_stage or current.build < target.build),
        "<=": current <= target and (current_stage <= target_stage or current.build <= target.build),
        "==": current == target and (current_stage == target_stage or current.build == target.build),
    }.get(op, False)


def get_proxy(base_url, prefix="", pass_prefix=False, proxy_plugin=None):
    async def proxy(request: Request, path: str):
        async def handler(r, p):
            query = request.url.query
            if query: p = f"{p}?{query}"

            if pass_prefix: url = f"{base_url}{prefix}/{p}"
            else: url = f"{base_url}/{p}"

            resp = await _proxy_client.request(
                r.method,
                url,
                headers=httpx.Headers(r.headers),
                content=await r.body()
            )

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers)
            )

        if proxy_plugin:
            return await proxy_plugin(request, path, handler)
        return await handler(request, path)
    return proxy


def get_websocket_proxy(base_url, prefix="", pass_prefix=False, proxy_plugin=None):
    async def websocket_proxy(websocket: WebSocket, path: str):
        async def handler(ws, p):
            query = ws.url.query
            if query: p = f"{p}?{query}"

            if pass_prefix: url = f"{base_url}{prefix}/{p}"
            else: url = f"{base_url}/{p}"

            ws_url = url.replace("http", "ws")

            subprotocol = ws.headers.get("sec-websocket-protocol")
            await ws.accept(subprotocol=subprotocol)

            async with websockets.connect(
                    ws_url, subprotocols=[
                        prot.strip() for prot in subprotocol.split(",")
                    ] if subprotocol else None
            ) as proxy_ws:

                async def client_to_server():
                    try:
                        while True:
                            msg = await ws.receive_text()
                            await proxy_ws.send(msg)
                    except (WebSocketDisconnect, asyncio.CancelledError):
                        pass

                async def server_to_client():
                    async for msg in proxy_ws:
                        await ws.send_text(msg)

                task1 = asyncio.create_task(client_to_server())
                task2 = asyncio.create_task(server_to_client())

                done, pending = await asyncio.wait(
                    [task1, task2],
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending: task.cancel()

        if proxy_plugin:
            return await proxy_plugin(websocket, path, handler)
        return await handler(websocket, path)
    return websocket_proxy


def add_proxy(target, base_url, prefix="", pass_prefix=False, proxy_plugin=None):
    proxy = get_proxy(base_url, prefix, pass_prefix, proxy_plugin)
    websocket_proxy = get_websocket_proxy(base_url, prefix, pass_prefix, proxy_plugin)

    from webfluid import Fluid
    if isinstance(target, Fluid):
        target.api_route(
            f"{prefix}/{{path:path}}",
            methods=["GET","POST","PUT","DELETE","PATCH"]
        )(proxy)
        target.websocket(f"{prefix}/{{path:path}}")(websocket_proxy)
    else:
        target.app.api_route(
            f"{prefix}/{{path:path}}",
            methods=["GET","POST","PUT","DELETE","PATCH"]
        )(proxy)
        target.ws.websocket(f"{prefix}/{{path:path}}")(websocket_proxy)


async def close_proxy_client():
    await _proxy_client.aclose()
