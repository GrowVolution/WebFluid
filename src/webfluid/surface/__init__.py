from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from webfluid.surface.wf_node import (
        load_node, cli_entry as node_cli, node_cmd, node_proc
    )
    from webfluid.surface.wf_tailwind import (
        load_tailwind, generate_tailwind_css,
        generate_asset as generate_tailwind_asset,
        tailwind_cmd, cli_entry as tailwind_cli
    )
    from webfluid.surface.frontend import Frontend

dist = (Path(__file__).parent / "dist").resolve()

__all__ = [
    "dist",

    "load_node", "node_cli", "node_cmd", "node_proc",

    "load_tailwind", "generate_tailwind_css",
    "generate_tailwind_asset", "tailwind_cmd", "tailwind_cli",

    "Frontend"
]


def __getattr__(name):
    if name in {
        "load_node", "node_cli", "node_cmd", "node_proc"
    }:
        from . import wf_node
        if name == "node_cli":
            return getattr(wf_node, "cli_entry")
        return getattr(wf_node, name)

    if name in {
        "load_tailwind", "generate_tailwind_css",
        "generate_tailwind_asset", "tailwind_cmd", "tailwind_cli"
    }:
        from . import wf_tailwind
        if name == "tailwind_cli":
            return getattr(wf_tailwind, "cli_entry")
        if name == "generate_tailwind_asset":
            return getattr(wf_tailwind, "generate_asset")
        return getattr(wf_tailwind, name)

    if name == "Frontend":
        from .frontend import Frontend
        return Frontend

    raise AttributeError(name)


def __dir__(): return sorted(__all__)
