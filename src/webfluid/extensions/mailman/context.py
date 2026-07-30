from contextvars import ContextVar

from webfluid.core.context.base import BaseContext


class ClientContext(BaseContext):
    _ctx = ContextVar("mailman.client")

    def __init__(self, client, is_async):
        self.client = client
        self.is_async = is_async
