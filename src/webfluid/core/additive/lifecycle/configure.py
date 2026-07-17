import typer

from webfluid.utils.core import try_import


def configure(additive, config):
    if additive.base: additive.base.configure(config)

    mod = try_import(f"{additive.import_name}.config")
    if mod is None: return

    setup = getattr(mod, "setup", None)
    if setup is None: return
    elif not isinstance(setup, dict):
        typer.secho(f"[{additive.name}] Attribute 'setup' in '{additive.import_name}.config' must be a dict.",
                    fg=typer.colors.YELLOW)
        return

    from webfluid.cli import questions
    config[additive.id] = {}

    for key, settings in setup.items():
        if "type" not in settings:
            typer.secho(f"[{additive.name}] Missing 'type' in setup settings for '{key}'.",
                        fg=typer.colors.YELLOW)
            continue
        elif settings["type"] not in {"select", "checkbox", "text", "confirm", "password", "auto"}:
            typer.secho(f"[{additive.name}] Invalid 'type' in setup settings for '{key}': {settings['type']}.",
                        fg=typer.colors.YELLOW)
            continue

        key_type = settings["type"]
        if key_type != "auto" and "message" not in settings:
            typer.secho(f"[{additive.name}] Missing 'message' in setup settings for '{key}'.",
                        fg=typer.colors.YELLOW)
            continue
        elif key_type == "auto" and "value" not in settings:
            typer.secho(f"[{additive.name}] Missing 'value' in setup settings for '{key}'.",
                        fg=typer.colors.YELLOW)
            continue

        if key_type == "auto":
            config[additive.id][key] = settings["value"]
            continue

        question = getattr(questions, key_type)
        message = settings["message"]
        kwargs = settings.get("kwargs", {})

        config[additive.id][key] = question(message, **kwargs).ask()
