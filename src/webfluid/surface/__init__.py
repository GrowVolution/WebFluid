from pathlib import Path

dist = (Path(__file__).parent / "dist").resolve()

__all__ = [
    "dist",

    "load_node", "node_cli", "node_cmd", "node_proc",

    "load_tailwind", "generate_tailwind_css", "generate_tailwind_asset",
    "tailwind_cmd", "tailwind_cli",

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
        "load_tailwind", "generate_tailwind_css", "generate_tailwind_asset",
        "tailwind_cmd", "tailwind_cli"
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
