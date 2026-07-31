from . import api
from .lifecycle import install_request_logger, install_error_pages
from .context import install_context
from .error import install_error_handler


def setup_processing(fluid):
    install_request_logger(fluid)
    install_error_pages(fluid)

    api.identity.add_route(fluid)
    api.url_for.add_route(fluid)

    install_context(fluid)
    install_error_handler(fluid)
