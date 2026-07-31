from starlette.requests import Request
from starlette.responses import Response

from webfluid.core.context.fluid import FluidContext


def _buffered(status, headers, chunks):
    response = Response(status_code=status)
    response.body = b"".join(chunks)
    response.raw_headers = headers
    return response


class RequestMiddleware:
    def __init__(self, app, fluid, request_lifecycle):
        self.app = app
        self.fluid = fluid
        self.lifecycle = request_lifecycle

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        if self.fluid.static_prefixes.matches(scope["path"]):
            return await self.app(scope, receive, send)

        async with FluidContext(self.fluid, Request(scope, receive)):
            response = await self.lifecycle.process_before()
            if response is not None:
                return await response(scope, receive, send)

            if not len(self.lifecycle.after):
                return await self.app(scope, receive, send)

            await self._process(scope, receive, send, self.lifecycle)

    async def _process(self, scope, receive, send, lifecycle):
        start = None
        chunks = []
        streaming = False

        async def capture(message):
            nonlocal start, streaming

            if message["type"] == "http.response.start":
                start = message
                return

            if message["type"] != "http.response.body" or streaming:
                return await send(message)

            if message.get("more_body"):
                streaming = True
                await send(start)
                for chunk in chunks:
                    await send({
                        "type": "http.response.body",
                        "body": chunk, "more_body": True
                    })
                chunks.clear()
                return await send(message)

            chunks.append(message.get("body", b""))

        await self.app(scope, receive, capture)
        if streaming or start is None: return

        response = await lifecycle.process_after(
            _buffered(start["status"], start["headers"], chunks)
        )
        await response(scope, receive, send)


def add(fluid, request_lifecycle):
    fluid.add_middleware(
        RequestMiddleware,
        fluid=fluid, request_lifecycle=request_lifecycle
    )
