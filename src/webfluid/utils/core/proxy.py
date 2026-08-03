from fastapi import Request, Response, WebSocket
from starlette.websockets import WebSocketDisconnect
import httpx, asyncio, websockets

_proxy_client = None

_SKIPPED_HEADERS = frozenset({
    "content-encoding", "content-length", "transfer-encoding", "connection"
})


def proxy_client():
    global _proxy_client
    if _proxy_client is None:
        _proxy_client = httpx.AsyncClient()
    return _proxy_client


def get_proxy(base_url, prefix="", pass_prefix=False, proxy_plugin=None):
    async def proxy(request: Request, path: str):
        async def handler(r, p):
            query = request.url.query
            if query: p = f"{p}?{query}"

            if pass_prefix: url = f"{base_url}{prefix}/{p}"
            else: url = f"{base_url}/{p}"

            resp = await proxy_client().request(
                r.method,
                url,
                headers=httpx.Headers(r.headers),
                content=await r.body()
            )

            response = Response(
                content=resp.content,
                status_code=resp.status_code
            )
            response.raw_headers = [
                (key.encode(), value.encode())
                for key, value in resp.headers.multi_items()
                if key.lower() not in _SKIPPED_HEADERS
            ] + [(b"content-length", str(len(resp.content)).encode())]
            return response

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

            ws_url = url.replace("http", "ws", 1)

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
    global _proxy_client
    if _proxy_client is None: return

    await _proxy_client.aclose()
    _proxy_client = None
