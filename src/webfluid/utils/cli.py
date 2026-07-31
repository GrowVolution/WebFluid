from contextvars import ContextVar
from contextlib import contextmanager
from shutil import get_terminal_size
from tqdm import tqdm
import typer, sys

from webfluid.core.context.base import BaseContext


class CliContext(BaseContext):
    _ctx = ContextVar("utils.cli")

    def __init__(self, bar):
        self.bar = bar


@contextmanager
def progress_bar(description, length, **kwargs):
    kwargs.setdefault("ncols", get_terminal_size().columns - 1)
    with tqdm(
            desc=description, total=length,
            file=sys.stdout, **kwargs
    ) as bar:
        with CliContext(bar): yield bar


def download_file(url, dest):
    import requests
    typer.secho(f"Downloading '{url}'...", bold=True)
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest, "wb") as f, progress_bar(
                str(dest), total if total > 0 else None,
                unit="B", unit_scale=True
        ) as bar:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))
