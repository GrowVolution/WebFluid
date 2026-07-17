from webfluid.utils.core import safe_execute


def add_http_middleware(additive):

    def middleware(call_next):
        async def wrapper(*args, **kwargs):
            response = await additive._request_lifecycle.process_before()
            if response is not None: return response
            response = await safe_execute(call_next, True, *args, **kwargs)
            response = await additive._request_lifecycle.process_after(response)
            return response
        return wrapper

    additive.api.http_middleware(middleware)
    additive.app.http_middleware(middleware)
