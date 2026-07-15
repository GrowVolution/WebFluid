from webfluid.core.context import FluidContext


def add(fluid):
    @fluid.middleware("http")
    async def middleware(request, call_next):
        path = request.url.path
        if fluid.static_prefixes.matches(path):
            return await call_next(request)

        async with FluidContext(fluid, request):
            response = await fluid._request_lifecycle.process_before()
            if response is not None: return response
            response = await call_next(request)
            response = await fluid._request_lifecycle.process_after(response)
            return response
