from .main import run


def cli_entry(app):
    app.command()(run)
