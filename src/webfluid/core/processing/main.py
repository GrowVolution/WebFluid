from . import lifecycle, api
from .context import add_context_processor
from .error import add_exception_handler


def setup_processing(fluid):
    lifecycle.before.add_hook(fluid)
    lifecycle.after.add_hook(fluid)

    api.identity.add_route(fluid)
    api.url_for.add_route(fluid)

    add_context_processor(fluid)
    add_exception_handler(fluid)
