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
    from webfluid.surface.frontend import (
        Frontend, setup_frontend, validate_config as validate_frontend_config
    )

dist = (Path(__file__).parent / "dist").resolve()

__all__ = [
    "dist",

    "load_node", "node_cli", "node_cmd", "node_proc",

    "load_tailwind", "generate_tailwind_css",
    "generate_tailwind_asset", "tailwind_cmd", "tailwind_cli",

    "Frontend", "setup_frontend", "validate_frontend_config"
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
        return getattr(wf_tailwind, name)

    if name in {
        "Frontend", "setup_frontend", "validate_frontend_config"
    }:
        from . import frontend
        if name == "validate_frontend_config":
            return getattr(frontend, "validate_config")
        return getattr(frontend, name)

    raise AttributeError(name)
