from contextvars import ContextVar
from contextlib import contextmanager
from tqdm import tqdm
import typer, requests, sys

from webfluid.core.constants import EXECUTION
from webfluid.core.context.base import BaseContext


class CliContext(BaseContext):
    _ctx = ContextVar("utils.cli")

    def __init__(self, bar):
        self.bar = bar


@contextmanager
def progress_bar(description, length, leave=True, **kwargs):
    with tqdm(
            desc=description, total=length,
            colour="green" if EXECUTION else None,
            file=sys.stdout, leave=leave, **kwargs
    ) as bar:
        with CliContext(bar): yield bar


def download_file(url, dest):
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
