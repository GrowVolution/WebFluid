from pathlib import Path
from webfluid.surface.wf_node import load_node, cli_entry as node_cli
from webfluid.surface.wf_tailwind import (setup_tailwind, generate_tailwind_css,
                                          generate_asset, cli_entry as tailwind_cli)
from webfluid.surface.frontend import Frontend, setup_frontend

dist = (Path(__file__).parent / "dist").resolve()

__all__ = [
    "dist",
    "load_node", "node_cli",
    "setup_tailwind", "generate_tailwind_css", "generate_asset", "tailwind_cli",
    "Frontend", "setup_frontend",
]
